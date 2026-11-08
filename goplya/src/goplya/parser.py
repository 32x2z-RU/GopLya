# Парсер (ручной рекурсивный спуск)

from typing import List, Optional, Union
from .tokens import Token, TokenType, KEYWORDS
from .ast import *
from .messages import error_msg


class ParseError(Exception):
    def __init__(self, message: str, line: int):
        self.message = message
        self.line = line
        super().__init__(f"{message} (строка {line})")


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
        self.current = tokens[0] if tokens else None

    def advance(self) -> Token:
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
            self.current = self.tokens[self.pos]
        return self.current

    def peek(self, offset: int = 1) -> Optional[Token]:
        peek_pos = self.pos + offset
        if peek_pos < len(self.tokens):
            return self.tokens[peek_pos]
        return None

    def match(self, *types: TokenType) -> bool:
        if self.current and self.current.type in types:
            self.advance()
            return True
        return False

    def expect(self, type_: TokenType, error_code: str = "E001", **kwargs) -> Token:
        if self.current and self.current.type == type_:
            token = self.current
            self.advance()
            return token
        line = self.current.line if self.current else 1
        raise ParseError(error_msg(error_code, line, **kwargs), line)

    def expect_keyword(self, keyword: str, error_code: str = "E001", **kwargs) -> Token:
        if self.current and self.current.type == TokenType.IDENTIFIER and self.current.value == keyword:
            token = self.current
            self.advance()
            return token
        line = self.current.line if self.current else 1
        raise ParseError(error_msg(error_code, line, **kwargs), line)

    def check(self, type_: TokenType) -> bool:
        return self.current and self.current.type == type_

    def check_keyword(self, keyword: str) -> bool:
        return self.current and self.current.type == TokenType.IDENTIFIER and self.current.value == keyword

    def at_end(self) -> bool:
        return self.current is None or self.current.type == TokenType.EOF

    def synchronize(self):
        """Восстановление после ошибки."""
        while not self.at_end():
            if self.current.type == TokenType.NEWLINE:
                self.advance()
                return
            if self.current.type in (TokenType.RBRACE, TokenType.RPAREN, TokenType.RBRACKET):
                return
            # Ключевые слова, начинающие операторы
            if self.current.type == TokenType.IDENTIFIER and self.current.value in (
                "пивас", "семка", "кортан", "гоп", "договорняк", "позвать",
                "чё_если", "грызи_пока", "по_каждому", "попробуй", "на_потом",
                "базарь", "отдай", "кидай", "хватит_епт", "дальше_епт",
                "по_братски", "слушай", "кинь_клич", "отстань"
            ):
                return
            self.advance()

    def _with_token(self, node, token: Token):
        """Устанавливает токен на узел и возвращает его."""
        node.token = token
        return node

    # --- Главная точка входа ---

    def parse(self) -> Program:
        header = self.parse_header()
        declarations = []
        while not self.at_end():
            while self.current and self.current.type == TokenType.NEWLINE:
                self.advance()
            if self.at_end():
                break
            try:
                decl = self.parse_declaration()
                if decl:
                    declarations.append(decl)
            except ParseError as e:
                # Ошибка уже сформатирована, пробрасываем
                raise
        return Program(header=header, declarations=declarations)

    def parse_header(self) -> Header:
        # Ожидаем: слыш ГопЛя 2.2 [мадмуазель]
        token = self.expect_keyword("слыш", "E008")
        self.expect_keyword("ГопЛя", "E008")
        
        # Версия (идентификатор или число)
        if self.check(TokenType.IDENTIFIER):
            version_token = self.expect(TokenType.IDENTIFIER, "E008")
            version = version_token.value
        elif self.check(TokenType.INTEGER) or self.check(TokenType.FLOAT):
            version_token = self.advance()
            version = version_token.value
        else:
            version = "2.2"
        
        # Проверка версии
        if version != "2.2":
            # Спецификация говорит: версия файла выше версии интерпретатора -> E012
            # Но мы просто фиксируем версию 2.2
            pass
        
        strict = False
        if self.check_keyword("мадмуазель"):
            self.advance()
            strict = True
        
        # Конец строки
        self.expect(TokenType.NEWLINE, "E008")
        
        header = Header(version=version, strict=strict)
        return self._with_token(header, token)

    # --- Объявления ---

    def parse_declaration(self) -> Optional[Declaration]:
        # Вынеси
        is_exported = False
        if self.check_keyword("вынеси"):
            self.advance()
            is_exported = True

        # Мадмуазель префикс для кортан/гоп
        is_strict_top = False
        if self.check_keyword("мадмуазель"):
            self.advance()
            is_strict_top = True

        if self.check_keyword("пивас"):
            return self.parse_pivas(is_exported)
        elif self.check_keyword("семка"):
            return self.parse_semka(is_exported)
        elif self.check_keyword("кортан"):
            return self.parse_kortan(is_exported, is_strict_top)
        elif self.check_keyword("гоп"):
            return self.parse_gop(is_exported, is_strict_top)
        elif self.check_keyword("договорняк"):
            return self.parse_dogovornyak(is_exported)
        elif self.check_keyword("позвать"):
            return self.parse_pozvat()
        else:
            # Оператор на верхнем уровне
            stmt = self.parse_statement()
            return stmt

    def parse_pivas(self, exported: bool) -> PivasDecl:
        token = self.expect_keyword("пивас")
        name_token = self.expect(TokenType.IDENTIFIER, "E004")
        name = name_token.value
        
        type_ann = None
        if self.match(TokenType.TERNARY_C):
            type_ann = self.parse_type_ann()
        
        self.expect(TokenType.ASSIGN, "E001")
        value = self.parse_expression()
        
        self.expect_newline_or_eof()
        
        decl = PivasDecl(name=name, type_ann=type_ann, value=value)
        return self._with_token(decl, token)

    def parse_semka(self, exported: bool) -> SemkaDecl:
        token = self.expect_keyword("семка")
        name_token = self.expect(TokenType.IDENTIFIER, "E004")
        name = name_token.value
        
        type_ann = None
        if self.match(TokenType.TERNARY_C):
            type_ann = self.parse_type_ann()
        
        value = None
        if self.match(TokenType.ASSIGN):
            value = self.parse_expression()
        
        self.expect_newline_or_eof()
        
        decl = SemkaDecl(name=name, type_ann=type_ann, value=value)
        return self._with_token(decl, token)

    def parse_kortan(self, exported: bool, is_strict_top: bool = False) -> KortanDecl:
        is_async = False
        is_strict = is_strict_top
        
        if not is_strict and self.check_keyword("мадмуазель"):
            self.advance()
            is_strict = True
        
        if self.check_keyword("сгоняй"):
            self.advance()
            is_async = True
        
        token = self.expect_keyword("кортан")
        
        # Лямбда без имени?
        if self.check(TokenType.LPAREN):
            # Анонимная лямбда - но в объявлении это не должно быть
            # Парсим как кортан с пустым именем
            name = ""
        else:
            name_token = self.expect(TokenType.IDENTIFIER, "E004")
            name = name_token.value
        
        params = self.parse_parameters()
        
        return_type = None
        if self.match(TokenType.TERNARY_C):
            return_type = self.parse_type_ann()
        
        # Тело: блок или "типа" выражение
        if self.check_keyword("типа"):
            self.advance()
            body = self.parse_expression()
            self.expect_newline_or_eof()
        else:
            body = self.parse_block()
        
        decl = KortanDecl(
            name=name, params=params, return_type=return_type,
            body=body, is_async=is_async, is_strict=is_strict
        )
        return self._with_token(decl, token)

    def parse_parameters(self) -> List[Parameter]:
        self.expect(TokenType.LPAREN, "E001")
        params = []
        
        if not self.check(TokenType.RPAREN):
            while True:
                name_token = self.expect(TokenType.IDENTIFIER, "E004")
                name = name_token.value
                
                type_ann = None
                if self.match(TokenType.TERNARY_C):
                    type_ann = self.parse_type_ann()
                
                default = None
                if self.match(TokenType.ASSIGN):
                    default = self.parse_expression()
                
                param = Parameter(name=name, type_ann=type_ann, default=default)
                params.append(self._with_token(param, name_token))
                
                if not self.match(TokenType.COMMA):
                    break
        
        self.expect(TokenType.RPAREN, "E001")
        return params

    def parse_type_ann(self) -> TypeAnn:
        name_token = self.expect(TokenType.IDENTIFIER, "E004")
        name = name_token.value
        nullable = False
        if self.match(TokenType.TERNARY_Q):  # ?
            nullable = True
        type_ann = TypeAnn(name=name, nullable=nullable)
        return self._with_token(type_ann, name_token)

    def parse_gop(self, exported: bool, is_strict_top: bool = False) -> GopDecl:
        is_strict = is_strict_top
        if not is_strict and self.check_keyword("мадмуазель"):
            self.advance()
            is_strict = True
        
        token = self.expect_keyword("гоп")
        name_token = self.expect(TokenType.IDENTIFIER, "E004")
        name = name_token.value
        
        parent = None
        if self.check_keyword("от_бати"):
            self.advance()
            parent_token = self.expect(TokenType.IDENTIFIER, "E004")
            parent = parent_token.value
        
        interfaces = []
        if self.check_keyword("по_договорняку"):
            self.advance()
            while True:
                iface_token = self.expect(TokenType.IDENTIFIER, "E004")
                interfaces.append(iface_token.value)
                if not self.match(TokenType.COMMA):
                    break
        
        self.expect(TokenType.LBRACE, "E001")
        members = []
        
        while not self.check(TokenType.RBRACE) and not self.at_end():
            if self.current.type == TokenType.NEWLINE:
                self.advance()
                continue
            
            modifier = None
            if self.current.type == TokenType.IDENTIFIER and self.current.value in ("у_подъезда", "по_семейному", "за_гаражами"):
                modifier = self.current.value
                self.advance()
            
            if self.check_keyword("семка"):
                field = self.parse_field()
                members.append(self._with_token(GopMember(modifier=modifier, field=field, method=None), self.current))
            elif self.check_keyword("кортан"):
                method = self.parse_kortan(False)
                members.append(self._with_token(GopMember(modifier=modifier, field=None, method=method), self.current))
            else:
                # Пропускаем неизвестное
                self.advance()
        
        self.expect(TokenType.RBRACE, "E001")
        
        decl = GopDecl(
            name=name, parent=parent, interfaces=interfaces,
            members=members, is_strict=is_strict
        )
        return self._with_token(decl, token)

    def parse_field(self) -> FieldDecl:
        token = self.expect_keyword("семка")
        name_token = self.expect(TokenType.IDENTIFIER, "E004")
        name = name_token.value
        
        type_ann = None
        if self.match(TokenType.TERNARY_C):
            type_ann = self.parse_type_ann()
        
        value = None
        if self.match(TokenType.ASSIGN):
            value = self.parse_expression()
        
        self.expect_newline_or_eof()
        
        decl = FieldDecl(name=name, type_ann=type_ann, value=value)
        return self._with_token(decl, token)

    def parse_dogovornyak(self, exported: bool) -> DogovornyakDecl:
        token = self.expect_keyword("договорняк")
        name_token = self.expect(TokenType.IDENTIFIER, "E004")
        name = name_token.value
        
        self.expect(TokenType.LBRACE, "E001")
        methods = []
        
        while not self.check(TokenType.RBRACE) and not self.at_end():
            if self.current.type == TokenType.NEWLINE:
                self.advance()
                continue
            
            if self.check_keyword("кортан"):
                method = self.parse_kortan(False)
                methods.append(method)
            else:
                self.advance()
        
        self.expect(TokenType.RBRACE, "E001")
        
        decl = DogovornyakDecl(name=name, methods=methods)
        return self._with_token(decl, token)

    def parse_pozvat(self) -> PozvatDecl:
        token = self.expect_keyword("позвать")
        
        # Два варианта: позвать "модуль" [как Имя]  или  позвать { имя, ... } из "модуль"
        if self.check(TokenType.STRING):
            module_token = self.expect(TokenType.STRING)
            module = module_token.value
            alias = None
            if self.check_keyword("как"):
                self.advance()
                alias_token = self.expect(TokenType.IDENTIFIER, "E004")
                alias = alias_token.value
            self.expect_newline_or_eof()
            decl = PozvatDecl(module=module, alias=alias, names=None)
            return self._with_token(decl, token)
        
        elif self.check(TokenType.LBRACE):
            self.advance()
            names = []
            while not self.check(TokenType.RBRACE) and not self.at_end():
                name_token = self.expect(TokenType.IDENTIFIER, "E004")
                names.append(name_token.value)
                if not self.match(TokenType.COMMA):
                    break
            self.expect(TokenType.RBRACE, "E001")
            
            self.expect_keyword("из", "E001")
            module_token = self.expect(TokenType.STRING)
            module = module_token.value
            
            self.expect_newline_or_eof()
            decl = PozvatDecl(module=module, alias=None, names=names)
            return self._with_token(decl, token)
        
        else:
            line = self.current.line if self.current else 1
            raise ParseError(error_msg("E001", line), line)

    # --- Операторы ---

    def parse_statement(self) -> Statement:
        if self.current.type == TokenType.NEWLINE:
            self.advance()
            return self.parse_statement()

        # Блок
        if self.check(TokenType.LBRACE):
            return self.parse_block()

        # Переменные
        if self.check_keyword("пивас"):
            return self.parse_pivas(False)
        if self.check_keyword("семка"):
            return self.parse_semka(False)

        # Управление
        if self.check_keyword("чё_если"):
            return self.parse_if()
        if self.check_keyword("грызи_пока"):
            return self.parse_while()
        if self.check_keyword("по_каждому"):
            return self.parse_for()
        if self.check_keyword("попробуй"):
            return self.parse_try()
        if self.check_keyword("на_потом"):
            return self.parse_na_potom()
        if self.check_keyword("базарь"):
            return self.parse_bazar()
        if self.check_keyword("отдай"):
            return self.parse_return()
        if self.check_keyword("кидай"):
            return self.parse_throw()
        if self.check_keyword("хватит_епт"):
            self.advance()
            self.expect_newline_or_eof()
            return self._with_token(BreakStmt(), self.current)
        if self.check_keyword("дальше_епт"):
            self.advance()
            self.expect_newline_or_eof()
            return self._with_token(ContinueStmt(), self.current)

        # Фирменные
        if self.check_keyword("по_братски"):
            return self.parse_po_bratski()
        if self.check_keyword("слушай"):
            return self.parse_slushai()
        if self.check_keyword("кинь_клич"):
            return self.parse_kin_klich()
        if self.check_keyword("отстань"):
            return self.parse_otstan()

        # Присваивание или выражение
        expr = self.parse_expression()
        
        # Проверяем присваивание после выражения (lvalue = ...)
        if self.current and self.current.type in (
            TokenType.ASSIGN, TokenType.PLUS_EQ, TokenType.MINUS_EQ,
            TokenType.STAR_EQ, TokenType.SLASH_EQ, TokenType.PERCENT_EQ
        ):
            op_token = self.current
            operator = op_token.value
            self.advance()
            value = self.parse_expression()
            self.expect_newline_or_eof()
            stmt = AssignStmt(target=expr, operator=operator, value=value)
            return self._with_token(stmt, op_token)

        self.expect_newline_or_eof()
        stmt = ExpressionStmt(expression=expr)
        return self._with_token(stmt, expr.token)

    def parse_block(self) -> Block:
        token = self.expect(TokenType.LBRACE, "E001")
        statements = []
        
        while not self.check(TokenType.RBRACE) and not self.at_end():
            if self.current.type == TokenType.NEWLINE:
                self.advance()
                continue
            try:
                stmt = self.parse_statement()
                statements.append(stmt)
            except ParseError:
                self.synchronize()
        
        self.expect(TokenType.RBRACE, "E002")
        block = Block(statements=statements)
        return self._with_token(block, token)

    def parse_if(self) -> IfStmt:
        token = self.expect_keyword("чё_если")
        self.expect(TokenType.LPAREN, "E001")
        condition = self.parse_expression()
        self.expect(TokenType.RPAREN, "E001")
        then_block = self.parse_block()
        
        elif_branches = []
        while self.check_keyword("а_чё_если"):
            self.advance()
            self.expect(TokenType.LPAREN, "E001")
            elif_cond = self.parse_expression()
            self.expect(TokenType.RPAREN, "E001")
            elif_block = self.parse_block()
            elif_branches.append((elif_cond, elif_block))
        
        else_block = None
        if self.check_keyword("а_нет"):
            self.advance()
            else_block = self.parse_block()
        
        stmt = IfStmt(condition=condition, then_block=then_block,
                      elif_branches=elif_branches, else_block=else_block)
        return self._with_token(stmt, token)

    def parse_while(self) -> WhileStmt:
        token = self.expect_keyword("грызи_пока")
        self.expect(TokenType.LPAREN, "E001")
        condition = self.parse_expression()
        self.expect(TokenType.RPAREN, "E001")
        body = self.parse_block()
        stmt = WhileStmt(condition=condition, body=body)
        return self._with_token(stmt, token)

    def parse_for(self) -> ForStmt:
        token = self.expect_keyword("по_каждому")
        self.expect(TokenType.LPAREN, "E001")
        
        var_token = self.expect(TokenType.IDENTIFIER, "E004")
        var_name = var_token.value
        
        if self.check_keyword("из"):
            self.advance()
            iterable = self.parse_expression()
            self.expect(TokenType.RPAREN, "E001")
            body = self.parse_block()
            stmt = ForStmt(var_name=var_name, iterable=iterable, body=body)
            return self._with_token(stmt, token)
        
        elif self.check_keyword("от"):
            self.advance()
            start = self.parse_expression()
            
            inclusive = True
            if self.check_keyword("до"):
                self.advance()
            elif self.check_keyword("мимо"):
                self.advance()
                inclusive = False
            else:
                line = self.current.line if self.current else 1
                raise ParseError(error_msg("E001", line), line)
            
            end = self.parse_expression()
            self.expect(TokenType.RPAREN, "E001")
            body = self.parse_block()
            stmt = ForStmt(var_name=var_name, range_start=start, 
                          range_end=end, range_inclusive=inclusive, body=body)
            return self._with_token(stmt, token)
        
        else:
            line = self.current.line if self.current else 1
            raise ParseError(error_msg("E001", line), line)

    def parse_try(self) -> TryStmt:
        token = self.expect_keyword("попробуй")
        try_block = self.parse_block()
        
        catch_blocks = []
        while self.check_keyword("предъявил"):
            self.advance()
            self.expect(TokenType.LPAREN, "E001")
            type_token = self.expect(TokenType.IDENTIFIER, "E004")
            exc_type = type_token.value
            var_token = self.expect(TokenType.IDENTIFIER, "E004")
            var_name = var_token.value
            self.expect(TokenType.RPAREN, "E001")
            catch_block = self.parse_block()
            catch_blocks.append(CatchBlock(exception_type=exc_type, var_name=var_name, block=catch_block))
        
        finally_block = None
        if self.check_keyword("по_понятиям"):
            self.advance()
            finally_block = self.parse_block()
        
        stmt = TryStmt(try_block=try_block, catch_blocks=catch_blocks, finally_block=finally_block)
        return self._with_token(stmt, token)

    def parse_na_potom(self) -> NaPotomStmt:
        token = self.expect_keyword("на_потом")
        stmt = self.parse_statement()
        return self._with_token(NaPotomStmt(statement=stmt), token)

    def parse_return(self) -> ReturnStmt:
        token = self.expect_keyword("отдай")
        value = None
        if not self.check(TokenType.NEWLINE) and not self.at_end():
            value = self.parse_expression()
        self.expect_newline_or_eof()
        stmt = ReturnStmt(value=value)
        return self._with_token(stmt, token)

    def parse_throw(self) -> ThrowStmt:
        token = self.expect_keyword("кидай")
        value = self.parse_expression()
        self.expect_newline_or_eof()
        stmt = ThrowStmt(value=value)
        return self._with_token(stmt, token)

    def parse_bazar(self) -> BazarStmt:
        token = self.expect_keyword("базарь")
        self.expect(TokenType.LPAREN, "E001")
        args = []
        if not self.check(TokenType.RPAREN):
            while True:
                args.append(self.parse_expression())
                if not self.match(TokenType.COMMA):
                    break
        self.expect(TokenType.RPAREN, "E001")
        self.expect_newline_or_eof()
        stmt = BazarStmt(args=args)
        return self._with_token(stmt, token)

    def parse_po_bratski(self) -> PoBratskiExpr:
        token = self.expect_keyword("по_братски")
        self.expect(TokenType.LPAREN, "E001")
        source = self.parse_expression()
        self.expect(TokenType.ARROW, "E001")  # =>
        targets = []
        while True:
            target = self.parse_expression()  # lvalue
            weight = None
            if self.match(TokenType.TERNARY_C, TokenType.TERNARY_C):
                weight = self.parse_expression()
            t = PoBratskiTarget(target=target, weight=weight)
            targets.append(self._with_token(t, self.current))
            if not self.match(TokenType.COMMA):
                break
        self.expect(TokenType.RPAREN, "E001")
        self.expect_newline_or_eof()
        stmt = PoBratskiExpr(source=source, targets=targets)
        return self._with_token(stmt, token)

    def parse_slushai(self) -> SlushaiStmt:
        token = self.expect_keyword("слушай")
        event_token = self.expect(TokenType.STRING, "E004")
        event_name = event_token.value
        self.expect(TokenType.ARROW, "E001")
        handler = self.parse_expression()
        self.expect_newline_or_eof()
        stmt = SlushaiStmt(event_name=event_name, handler=handler)
        return self._with_token(stmt, token)

    def parse_kin_klich(self) -> KinKlichStmt:
        token = self.expect_keyword("кинь_клич")
        event_token = self.expect(TokenType.STRING, "E004")
        event_name = event_token.value
        args = []
        if self.check(TokenType.LPAREN):
            self.advance()
            if not self.check(TokenType.RPAREN):
                while True:
                    args.append(self.parse_expression())
                    if not self.match(TokenType.COMMA):
                        break
            self.expect(TokenType.RPAREN, "E001")
        self.expect_newline_or_eof()
        stmt = KinKlichStmt(event_name=event_name, args=args)
        return self._with_token(stmt, token)

    def parse_otstan(self) -> OtstanStmt:
        token = self.expect_keyword("отстань")
        event_token = self.expect(TokenType.STRING, "E004")
        event_name = event_token.value
        self.expect_newline_or_eof()
        stmt = OtstanStmt(event_name=event_name)
        return self._with_token(stmt, token)

    # --- Выражения (приоритет от низшего к высшему) ---

    def parse_expression(self) -> Expression:
        return self.parse_ternary()

    def parse_ternary(self) -> Expression:
        expr = self.parse_null_coalesce()
        
        if self.match(TokenType.TERNARY_Q):  # ?
            then_expr = self.parse_expression()
            self.expect(TokenType.TERNARY_C, "E001")  # :
            else_expr = self.parse_ternary()  # правая ассоциативность
            return self._with_token(TernaryOp(condition=expr, then_expr=then_expr, else_expr=else_expr), self.current)
        
        return expr

    def parse_null_coalesce(self) -> Expression:
        expr = self.parse_logical_or()
        
        while self.match(TokenType.NULL_COALESCE):  # ??
            right = self.parse_logical_or()
            expr = self._with_token(BinaryOp(left=expr, operator="??", right=right), self.current)
        
        return expr

    def parse_logical_or(self) -> Expression:
        expr = self.parse_logical_and()
        
        while self.match(TokenType.LOGICAL_OR) or self.check_keyword("или_чё"):
            if self.current and self.current.type == TokenType.IDENTIFIER and self.current.value == "или_чё":
                self.advance()
                operator = "или_чё"
            else:
                operator = "||"
            right = self.parse_logical_and()
            expr = self._with_token(BinaryOp(left=expr, operator=operator, right=right), self.current)
        
        return expr

    def parse_logical_and(self) -> Expression:
        expr = self.parse_equality()
        
        while self.match(TokenType.LOGICAL_AND) or self.check_keyword("и_ещё"):
            if self.current and self.current.type == TokenType.IDENTIFIER and self.current.value == "и_ещё":
                self.advance()
                operator = "и_ещё"
            else:
                operator = "&&"
            right = self.parse_equality()
            expr = self._with_token(BinaryOp(left=expr, operator=operator, right=right), self.current)
        
        return expr

    def parse_equality(self) -> Expression:
        expr = self.parse_comparison()
        
        while self.match(TokenType.EQ, TokenType.NE):
            op_token = self.tokens[self.pos-1]
            operator = "==" if op_token.type == TokenType.EQ else "!="
            right = self.parse_comparison()
            expr = self._with_token(BinaryOp(left=expr, operator=operator, right=right), self.current)
        
        return expr

    def parse_comparison(self) -> Expression:
        expr = self.parse_additive()
        
        while self.match(TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            operator = self.tokens[self.pos-1].value
            right = self.parse_additive()
            expr = self._with_token(BinaryOp(left=expr, operator=operator, right=right), self.current)
        
        return expr

    def parse_additive(self) -> Expression:
        expr = self.parse_multiplicative()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            operator = self.tokens[self.pos-1].value
            right = self.parse_multiplicative()
            expr = self._with_token(BinaryOp(left=expr, operator=operator, right=right), self.current)
        
        return expr

    def parse_multiplicative(self) -> Expression:
        expr = self.parse_power()
        
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            operator = self.tokens[self.pos-1].value
            right = self.parse_power()
            expr = self._with_token(BinaryOp(left=expr, operator=operator, right=right), self.current)
        
        return expr

    def parse_power(self) -> Expression:
        expr = self.parse_unary()
        
        if self.match(TokenType.POWER):  # **
            right = self.parse_power()  # правая ассоциативность
            expr = self._with_token(BinaryOp(left=expr, operator="**", right=right), self.current)
        
        return expr

    def parse_unary(self) -> Expression:
        if self.match(TokenType.MINUS, TokenType.LOGICAL_NOT):
            operator = self.current.value if self.current else self.tokens[self.pos-1].value
            operand = self.parse_unary()
            return self._with_token(UnaryOp(operator=operator, operand=operand), self.current)
        
        if self.check_keyword("не_а") or self.check_keyword("подожди_пивас"):
            keyword = self.current.value
            self.advance()
            operand = self.parse_unary()
            return self._with_token(UnaryOp(operator=keyword, operand=operand), self.current)
        
        return self.parse_postfix()

    def parse_postfix(self) -> Expression:
        expr = self.parse_primary()
        
        while True:
            if self.match(TokenType.LPAREN):  # вызов
                args = []
                if not self.check(TokenType.RPAREN):
                    while True:
                        # Именованные аргументы: имя = выражение
                        if (self.check(TokenType.IDENTIFIER) and 
                            self.peek() and self.peek().type == TokenType.ASSIGN):
                            name_token = self.current
                            self.advance()  # имя
                            self.advance()  # =
                            value = self.parse_expression()
                            arg = Arg(name=name_token.value, value=value)
                            args.append(self._with_token(arg, name_token))
                        else:
                            value = self.parse_expression()
                            arg = Arg(name=None, value=value)
                            args.append(self._with_token(arg, value.token))
                        if not self.match(TokenType.COMMA):
                            break
                self.expect(TokenType.RPAREN, "E001")
                expr = self._with_token(CallExpr(callee=expr, args=args), self.current)
            
            elif self.match(TokenType.LBRACKET):  # индекс
                index = self.parse_expression()
                self.expect(TokenType.RBRACKET, "E001")
                expr = self._with_token(IndexExpr(object=expr, index=index), self.current)
            
            elif self.match(TokenType.SAFE_DOT):  # ?.
                name_token = self.expect(TokenType.IDENTIFIER, "E004")
                expr = self._with_token(MemberExpr(object=expr, name=name_token.value, safe=True), self.current)
            
            elif self.match(TokenType.DOT):  # .
                name_token = self.expect(TokenType.IDENTIFIER, "E004")
                expr = self._with_token(MemberExpr(object=expr, name=name_token.value, safe=False), self.current)
            
            else:
                break
        
        return expr

    def parse_primary(self) -> Expression:
        # Литералы
        if self.match(TokenType.INTEGER):
            value = int(self.tokens[self.pos-1].value)
            lit = Literal(value=value, lit_type='int')
            return self._with_token(lit, self.tokens[self.pos-1])
        
        if self.match(TokenType.FLOAT):
            value = float(self.tokens[self.pos-1].value)
            lit = Literal(value=value, lit_type='float')
            return self._with_token(lit, self.tokens[self.pos-1])
        
        if self.match(TokenType.STRING):
            # Интерполяция внутри строки
            return self.parse_string_with_interpolation(self.tokens[self.pos-1])
        
        if self.match(TokenType.TRUE):
            lit = Literal(value=True, lit_type='bool')
            return self._with_token(lit, self.tokens[self.pos-1])
        
        if self.match(TokenType.FALSE):
            lit = Literal(value=False, lit_type='bool')
            return self._with_token(lit, self.tokens[self.pos-1])
        
        if self.match(TokenType.NULL):
            lit = Literal(value=None, lit_type='null')
            return self._with_token(lit, self.tokens[self.pos-1])
        
        # Новый объект
        if self.check_keyword("новый"):
            return self.parse_new()
        
        # Лямбда
        if self.check_keyword("кортан"):
            return self.parse_lambda()
        
        # Идентификаторы
        if self.match(TokenType.IDENTIFIER):
            name = self.tokens[self.pos-1].value
            if name == "сам":
                return self._with_token(SelfExpr(), self.tokens[self.pos-1])
            elif name == "батя":
                return self._with_token(BatyaExpr(), self.tokens[self.pos-1])
            else:
                ident = Identifier(name=name)
                return self._with_token(ident, self.tokens[self.pos-1])
        
        # Кучка
        if self.match(TokenType.LBRACKET):
            elements = []
            if not self.check(TokenType.RBRACKET):
                while True:
                    elements.append(self.parse_expression())
                    if not self.match(TokenType.COMMA):
                        break
            self.expect(TokenType.RBRACKET, "E001")
            lst = ListLiteral(elements=elements)
            return self._with_token(lst, self.current)
        
        # Общак
        if self.match(TokenType.LBRACE):
            entries = []
            if not self.check(TokenType.RBRACE):
                while True:
                    key = self.parse_expression()
                    self.expect(TokenType.TERNARY_C, "E001")
                    value = self.parse_expression()
                    entries.append((key, value))
                    if not self.match(TokenType.COMMA):
                        break
            self.expect(TokenType.RBRACE, "E001")
            dct = DictLiteral(entries=entries)
            return self._with_token(dct, self.current)
        
        # Скобки
        if self.match(TokenType.LPAREN):
            expr = self.parse_expression()
            self.expect(TokenType.RPAREN, "E001")
            return expr
        
        line = self.current.line if self.current else 1
        raise ParseError(error_msg("E001", line), line)

    def parse_string_with_interpolation(self, token: Token) -> Expression:
        """Парсит строку с интерполяцией {выражение}."""
        raw = token.value
        parts = []
        i = 0
        current_str = ""
        
        while i < len(raw):
            if raw[i] == '{' and (i == 0 or raw[i-1] != '\\'):
                # Начало интерполяции
                if current_str:
                    parts.append(current_str)
                    current_str = ""
                
                # Находим закрывающую скобку с учётом вложенности
                depth = 1
                j = i + 1
                while j < len(raw) and depth > 0:
                    if raw[j] == '{' and (j == 0 or raw[j-1] != '\\'):
                        depth += 1
                    elif raw[j] == '}' and (j == 0 or raw[j-1] != '\\'):
                        depth -= 1
                    j += 1
                
                if depth != 0:
                    # Незакрытая скобка в интерполяции
                    raise ParseError("Незакрытая интерполяция в строке", token.line)
                
                # Парсим выражение внутри
                inner = raw[i+1:j-1]
                # Создаём мини-лексер и парсер для выражения
                from .lexer import Lexer
                inner_lexer = Lexer(inner)
                inner_tokens = inner_lexer.tokenize()
                inner_parser = Parser(inner_tokens)
                inner_expr = inner_parser.parse_expression()
                parts.append(inner_expr)
                
                i = j
            else:
                current_str += raw[i]
                i += 1
        
        if current_str:
            parts.append(current_str)
        
        if len(parts) == 1 and isinstance(parts[0], str):
            lit = Literal(value=parts[0], lit_type='string')
            return self._with_token(lit, token)
        
        interp = Interpolation(parts=parts)
        return self._with_token(interp, token)

    def parse_new(self) -> NewExpr:
        token = self.expect_keyword("новый")
        class_token = self.expect(TokenType.IDENTIFIER, "E004")
        class_name = class_token.value
        
        args = []
        if self.check(TokenType.LPAREN):
            self.advance()
            if not self.check(TokenType.RPAREN):
                while True:
                    if (self.check(TokenType.IDENTIFIER) and 
                        self.peek() and self.peek().type == TokenType.ASSIGN):
                        name_token = self.current
                        self.advance()
                        self.advance()  # =
                        value = self.parse_expression()
                        arg = Arg(name=name_token.value, value=value)
                        args.append(self._with_token(arg, name_token))
                    else:
                        value = self.parse_expression()
                        arg = Arg(name=None, value=value)
                        args.append(self._with_token(arg, value.token))
                    if not self.match(TokenType.COMMA):
                        break
            self.expect(TokenType.RPAREN, "E001")
        
        is_ring = False
        if self.check_keyword("по_кругу"):
            self.advance()
            is_ring = True
        
        expr = NewExpr(class_name=class_name, args=args, is_ring=is_ring)
        return self._with_token(expr, class_token)

    def parse_lambda(self) -> LambdaExpr:
        is_async = False
        is_strict = False
        if self.check_keyword("мадмуазель"):
            self.advance()
            is_strict = True
        if self.check_keyword("сгоняй"):
            self.advance()
            is_async = True
        
        token = self.expect_keyword("кортан")
        params = self.parse_parameters()
        
        if self.check_keyword("типа"):
            self.advance()
            body = self.parse_expression()
        else:
            body = self.parse_block()
        
        expr = LambdaExpr(params=params, body=body, is_async=is_async, is_strict=is_strict)
        return self._with_token(expr, token)

    def expect_newline_or_eof(self):
        """Ожидает конец строки или EOF."""
        while self.current and self.current.type == TokenType.NEWLINE:
            self.advance()
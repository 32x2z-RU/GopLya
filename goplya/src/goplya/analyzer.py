# Анализатор (статические проверки: области видимости, константы, await, мадмуазель)

from typing import List, Dict, Set, Optional, Any
from .ast import *
from .messages import error_msg, warning_msg, type_genitive
from .tokens import KEYWORDS


class AnalysisError(Exception):
    def __init__(self, message: str, line: int):
        self.message = message
        self.line = line
        super().__init__(f"{message} (строка {line})")


class Scope:
    """Область видимости для статического анализа."""
    
    def __init__(self, parent: Optional['Scope'] = None, is_function: bool = False, is_strict: bool = False):
        self.parent = parent
        self.is_function = is_function
        self.is_strict = is_strict
        self.variables: Dict[str, VariableInfo] = {}
        self.constants: Set[str] = set()
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.interfaces: Dict[str, InterfaceInfo] = {}
        self.imports: Dict[str, str] = {}  # alias -> module
    
    def define_var(self, name: str, info: 'VariableInfo'):
        if name in self.variables:
            # Переопределение в той же области - ошибка
            raise AnalysisError(f"Переменная «{name}» уже объявлена в этой области", info.line)
        self.variables[name] = info
    
    def define_const(self, name: str, info: 'VariableInfo'):
        self.define_var(name, info)
        self.constants.add(name)
    
    def resolve_var(self, name: str) -> Optional['VariableInfo']:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.resolve_var(name)
        return None
    
    def is_const(self, name: str) -> bool:
        if name in self.constants:
            return True
        if self.parent:
            return self.parent.is_const(name)
        return False


@dataclass
class VariableInfo:
    name: str
    type_ann: Optional[TypeAnn]
    line: int
    is_const: bool
    initialized: bool = False


@dataclass
class FunctionInfo:
    name: str
    params: List[Parameter]
    return_type: Optional[TypeAnn]
    is_async: bool
    is_strict: bool
    line: int


@dataclass
class ClassInfo:
    name: str
    parent: Optional[str]
    interfaces: List[str]
    fields: Dict[str, FieldDecl]
    methods: Dict[str, FunctionInfo]
    modifiers: Dict[str, str]
    is_strict: bool
    line: int


@dataclass
class InterfaceInfo:
    name: str
    methods: List[FunctionInfo]
    line: int


class Analyzer:
    """Статический анализатор."""
    
    def __init__(self, program: Program, strict_mode: bool = False):
        self.program = program
        self.global_scope = Scope(is_strict=strict_mode)
        self.current_scope = self.global_scope
        self.current_function: Optional[FunctionInfo] = None
        self.current_class: Optional[ClassInfo] = None
        self.in_async_function = False
        self.errors: List[tuple[str, int]] = []  # (message, line)
        self.warnings: List[tuple[str, int]] = []
        self._register_builtins()
    
    def _register_builtins(self):
        """Регистрирует встроенные имена."""
        builtins = {
            'Косяк', 'БамперКосяк', 'Сижка', 'сигара', 'папироска',
            'Буфера', 'Вот_это_буфера', 'Гонец', 'братва',
            'перекур', 'шухер', 'отбой', 'Дворник', 'дели_целиком',
            'спроси', 'корень', 'округли', 'модуль', 'в_текст',
            'прочитай', 'запиши', 'есть', 'достань',
            'случайное', 'выбери', 'зерно', 'сейчас', 'сегодня',
            'базарь',
        }
        for name in builtins:
            self.global_scope.variables[name] = VariableInfo(
                name=name, type_ann=None, line=0, is_const=True, initialized=True
            )
    
    def analyze(self) -> tuple[List[tuple[str, int]], List[tuple[str, int]]]:
        """Запускает анализ программы."""
        # Сначала проход по объявлениям для регистрации
        for decl in self.program.declarations:
            self._register_declaration(decl)
        
        # Второй проход — проверка тел
        for decl in self.program.declarations:
            self._check_declaration(decl)
        
        return self.errors, self.warnings
    
    def _register_declaration(self, decl: Declaration):
        if isinstance(decl, PivasDecl):
            info = VariableInfo(decl.name, decl.type_ann, decl.line(), True)
            self.current_scope.define_const(decl.name, info)
        elif isinstance(decl, SemkaDecl):
            info = VariableInfo(decl.name, decl.type_ann, decl.line(), False)
            self.current_scope.define_var(decl.name, info)
        elif isinstance(decl, KortanDecl):
            info = FunctionInfo(
                decl.name, decl.params, decl.return_type,
                decl.is_async, decl.is_strict, decl.line()
            )
            self.current_scope.functions[decl.name] = info
        elif isinstance(decl, GopDecl):
            fields = {m.field.name: m.field for m in decl.members if m.field}
            methods = {}
            modifiers = {}
            for m in decl.members:
                if m.method:
                    methods[m.method.name] = FunctionInfo(
                        m.method.name, m.method.params, m.method.return_type,
                        m.method.is_async, m.method.is_strict, m.method.line()
                    )
                if m.field:
                    modifiers[m.field.name] = m.modifier or 'у_подъезда'
                if m.method:
                    modifiers[m.method.name] = m.modifier or 'у_подъезда'
            
            info = ClassInfo(
                decl.name, decl.parent, decl.interfaces, fields, methods,
                modifiers, decl.is_strict, decl.line()
            )
            self.current_scope.classes[decl.name] = info
        elif isinstance(decl, DogovornyakDecl):
            methods = []
            for m in decl.methods:
                methods.append(FunctionInfo(
                    m.name, m.params, m.return_type,
                    m.is_async, m.is_strict, m.line()
                ))
            info = InterfaceInfo(decl.name, methods, decl.line())
            self.global_scope.interfaces[decl.name] = info
        elif isinstance(decl, PozvatDecl):
            if decl.alias:
                self.current_scope.imports[decl.alias] = decl.module
            else:
                # Импорт без алиаса — имена добавляются в глобальную область
                pass  # будет разрешено при проверке
    
    def _check_declaration(self, decl: Declaration):
        if isinstance(decl, PivasDecl):
            self._check_expression(decl.value)
            self.current_scope.variables[decl.name].initialized = True
        elif isinstance(decl, SemkaDecl):
            if decl.value:
                self._check_expression(decl.value)
            self.current_scope.variables[decl.name].initialized = True
        elif isinstance(decl, KortanDecl):
            self._check_kortan(decl)
        elif isinstance(decl, GopDecl):
            self._check_gop(decl)
        elif isinstance(decl, DogovornyakDecl):
            pass  # уже зарегистрирован
        elif isinstance(decl, PozvatDecl):
            pass
        elif isinstance(decl, Statement):
            self._check_statement(decl)
    
    def _check_kortan(self, decl: KortanDecl):
        prev_func = self.current_function
        prev_async = self.in_async_function
        prev_scope = self.current_scope
        
        is_strict = decl.is_strict or self.current_scope.is_strict
        self.current_scope = Scope(parent=self.current_scope, is_function=True, is_strict=is_strict)
        self.current_function = FunctionInfo(decl.name, decl.params, decl.return_type, decl.is_async, is_strict, decl.line())
        self.in_async_function = decl.is_async
        
        # Проверка параметров
        for param in decl.params:
            var_info = VariableInfo(param.name, param.type_ann, decl.line(), False)
            self.current_scope.define_var(param.name, var_info)
            
            # Мадмуазель: все параметры должны иметь аннотации
            if is_strict and param.type_ann is None:
                self.errors.append((error_msg('E011', decl.line(), name=param.name), decl.line()))
        
        # Мадмуазель: возвращаемое значение должно иметь аннотацию
        if is_strict and decl.return_type is None and decl.name:
            self.errors.append((error_msg('E011', decl.line(), name=f"{decl.name} (возврат)"), decl.line()))
        
        # Проверка тела
        if isinstance(decl.body, Block):
            for stmt in decl.body.statements:
                self._check_statement(stmt)
        else:
            self._check_expression(decl.body)
        
        self.current_scope = prev_scope
        self.current_function = prev_func
        self.in_async_function = prev_async
    
    def _check_gop(self, decl: GopDecl):
        prev_class = self.current_class
        prev_scope = self.current_scope
        
        is_strict = decl.is_strict or self.current_scope.is_strict
        self.current_scope = Scope(parent=self.current_scope, is_strict=is_strict)
        self.current_class = self.current_scope.classes.get(decl.name)
        
        # Проверка реализации договорняков
        for iface_name in decl.interfaces:
            iface = self.global_scope.interfaces.get(iface_name)
            if iface:
                for iface_method in iface.methods:
                    if iface_method.name not in self.current_class.methods:
                        self.errors.append((
                            error_msg('E005', decl.line(), method=iface_method.name),
                            decl.line()
                        ))
        
        # Проверка полей и методов
        for member in decl.members:
            if member.field:
                if member.field.value:
                    self._check_expression(member.field.value)
            if member.method:
                self._check_kortan(member.method)
        
        self.current_scope = prev_scope
        self.current_class = prev_class
    
    def _check_statement(self, stmt: Statement):
        if isinstance(stmt, Block):
            for s in stmt.statements:
                self._check_statement(s)
        elif isinstance(stmt, PivasDecl):
            # Регистрируем константу в текущей области видимости
            info = VariableInfo(stmt.name, stmt.type_ann, stmt.line(), True)
            self.current_scope.define_const(stmt.name, info)
            self._check_expression(stmt.value)
            self.current_scope.variables[stmt.name].initialized = True
        elif isinstance(stmt, SemkaDecl):
            # Регистрируем переменную в текущей области видимости
            info = VariableInfo(stmt.name, stmt.type_ann, stmt.line(), False)
            self.current_scope.define_var(stmt.name, info)
            if stmt.value:
                self._check_expression(stmt.value)
            self.current_scope.variables[stmt.name].initialized = True
        elif isinstance(stmt, IfStmt):
            self._check_expression(stmt.condition)
            self._check_statement(stmt.then_block)
            for cond, block in stmt.elif_branches:
                self._check_expression(cond)
                self._check_statement(block)
            if stmt.else_block:
                self._check_statement(stmt.else_block)
        elif isinstance(stmt, WhileStmt):
            self._check_expression(stmt.condition)
            self._check_statement(stmt.body)
            
            # W004: бесконечный цикл с константным правда
            if (isinstance(stmt.condition, Literal) and stmt.condition.value is True):
                self.warnings.append((warning_msg(W004, stmt.line()), stmt.line()))
        elif isinstance(stmt, ForStmt):
            if stmt.iterable:
                self._check_expression(stmt.iterable)
            else:
                if stmt.range_start:
                    self._check_expression(stmt.range_start)
                if stmt.range_end:
                    self._check_expression(stmt.range_end)
            
            prev_scope = self.current_scope
            self.current_scope = Scope(parent=self.current_scope)
            self.current_scope.define_var(stmt.var_name, VariableInfo(stmt.var_name, None, stmt.line(), False))
            self._check_statement(stmt.body)
            self.current_scope = prev_scope
        elif isinstance(stmt, TryStmt):
            self._check_statement(stmt.try_block)
            for catch in stmt.catch_blocks:
                prev_scope = self.current_scope
                self.current_scope = Scope(parent=self.current_scope)
                self.current_scope.define_var(catch.var_name, VariableInfo(catch.var_name, None, catch.line(), False))
                self._check_statement(catch.block)
                self.current_scope = prev_scope
            if stmt.finally_block:
                self._check_statement(stmt.finally_block)
        elif isinstance(stmt, NaPotomStmt):
            self._check_statement(stmt.statement)
        elif isinstance(stmt, ReturnStmt):
            if stmt.value:
                self._check_expression(stmt.value)
        elif isinstance(stmt, ThrowStmt):
            self._check_expression(stmt.value)
        elif isinstance(stmt, BazarStmt):
            for arg in stmt.args:
                self._check_expression(arg)
        elif isinstance(stmt, AssignStmt):
            self._check_lvalue(stmt.target)
            self._check_expression(stmt.value)
        elif isinstance(stmt, ExpressionStmt):
            self._check_expression(stmt.expression)
        elif isinstance(stmt, SlushaiStmt):
            self._check_expression(stmt.handler)
        elif isinstance(stmt, KinKlichStmt):
            for arg in stmt.args:
                self._check_expression(arg)
        elif isinstance(stmt, PoBratskiExpr):
            self._check_expression(stmt.source)
            for target in stmt.targets:
                self._check_lvalue(target.target)
                if target.weight:
                    self._check_expression(target.weight)
        # Break/Continue/Otstan не требуют проверки
    
    def _check_expression(self, expr: Expression):
        if isinstance(expr, Literal):
            pass
        elif isinstance(expr, Identifier):
            self._check_identifier(expr)
        elif isinstance(expr, SelfExpr):
            pass
        elif isinstance(expr, BatyaExpr):
            if not self.current_class or not self.current_class.parent:
                self.errors.append((error_msg('E004', expr.line(), name="батя"), expr.line()))
        elif isinstance(expr, BinaryOp):
            self._check_expression(expr.left)
            self._check_expression(expr.right)
            
            # Проверка типов в мадмуазель режиме
            if self.current_scope.is_strict:
                self._check_strict_binary(expr)
        elif isinstance(expr, UnaryOp):
            self._check_expression(expr.operand)
            if expr.operator == 'подожди_пивас':
                if not self.in_async_function:
                    self.errors.append((error_msg('E006', expr.line()), expr.line()))
        elif isinstance(expr, TernaryOp):
            self._check_expression(expr.condition)
            self._check_expression(expr.then_expr)
            self._check_expression(expr.else_expr)
        elif isinstance(expr, CallExpr):
            self._check_expression(expr.callee)
            for arg in expr.args:
                self._check_expression(arg.value)
        elif isinstance(expr, IndexExpr):
            self._check_expression(expr.object)
            self._check_expression(expr.index)
        elif isinstance(expr, MemberExpr):
            self._check_expression(expr.object)
        elif isinstance(expr, NewExpr):
            for arg in expr.args:
                self._check_expression(arg.value)
        elif isinstance(expr, ListLiteral):
            for e in expr.elements:
                self._check_expression(e)
        elif isinstance(expr, DictLiteral):
            for k, v in expr.entries:
                self._check_expression(k)
                self._check_expression(v)
        elif isinstance(expr, Interpolation):
            for part in expr.parts:
                if isinstance(part, Expression):
                    self._check_expression(part)
        elif isinstance(expr, LambdaExpr):
            self._check_lambda(expr)
        elif isinstance(expr, PoBratskiExpr):
            self._check_expression(expr.source)
            for target in expr.targets:
                self._check_lvalue(target.target)
                if target.weight:
                    self._check_expression(target.weight)
    
    def _check_lambda(self, expr: LambdaExpr):
        prev_func = self.current_function
        prev_async = self.in_async_function
        prev_scope = self.current_scope
        
        is_strict = expr.is_strict or self.current_scope.is_strict
        self.current_scope = Scope(parent=self.current_scope, is_function=True, is_strict=is_strict)
        self.in_async_function = expr.is_async
        
        for param in expr.params:
            var_info = VariableInfo(param.name, param.type_ann, expr.line(), False)
            self.current_scope.define_var(param.name, var_info)
            
            if is_strict and param.type_ann is None:
                self.errors.append((error_msg('E011', expr.line(), name=param.name), expr.line()))
        
        if isinstance(expr.body, Block):
            for stmt in expr.body.statements:
                self._check_statement(stmt)
        else:
            self._check_expression(expr.body)
        
        self.current_scope = prev_scope
        self.current_function = prev_func
        self.in_async_function = prev_async
    
    def _check_identifier(self, expr: Identifier):
        info = self.current_scope.resolve_var(expr.name)
        if info is None:
            # Проверяем функции и классы
            if expr.name in self.current_scope.functions:
                return
            if expr.name in self.current_scope.classes:
                return
            if expr.name in self.global_scope.interfaces:
                return
            if expr.name in self.current_scope.imports:
                return
            
            self.errors.append((error_msg('E004', expr.line(), name=expr.name), expr.line()))
        else:
            if not info.initialized:
                # Использование до инициализации - предупреждение или ошибка?
                pass
    
    def _check_lvalue(self, expr: Expression):
        if isinstance(expr, Identifier):
            if self.current_scope.is_const(expr.name):
                self.errors.append((error_msg('E003', expr.line()), expr.line()))
        elif isinstance(expr, MemberExpr) or isinstance(expr, IndexExpr):
            self._check_expression(expr.object)
            if isinstance(expr, IndexExpr):
                self._check_expression(expr.index)
        else:
            self.errors.append((error_msg('E003', expr.line()), expr.line()))
    
    def _check_strict_binary(self, expr: BinaryOp):
        """Проверка типов в строгом режиме."""
        # Получаем типы операндов (если известны статически)
        left_type = self._infer_type(expr.left)
        right_type = self._infer_type(expr.right)
        
        if left_type and right_type:
            # Проверка сложения строки с числом
            if expr.operator == '+':
                if left_type == 'текст' and right_type != 'текст':
                    self.errors.append((
                        error_msg('E009', expr.line(), 
                                got=right_type, 
                                expected_gen=type_genitive('текст')),
                        expr.line()
                    ))
                if right_type == 'текст' and left_type != 'текст':
                    self.errors.append((
                        error_msg('E009', expr.line(), 
                                got=left_type, 
                                expected_gen=type_genitive('текст')),
                        expr.line()
                    ))
            
            # Неявные приведения запрещены, кроме целое -> дробь
            if left_type != right_type:
                # Проверяем совместимость
                if not (left_type == 'целое' and right_type == 'дробь') and \
                   not (left_type == 'дробь' and right_type == 'целое'):
                    # Для операторов сравнения допустимо
                    if expr.operator not in ('==', '!=', '<', '>', '<=', '>='):
                        self.errors.append((
                            error_msg('E009', expr.line(),
                                    got=right_type,
                                    expected_gen=type_genitive(left_type)),
                            expr.line()
                        ))
    
    def _infer_type(self, expr: Expression) -> Optional[str]:
        """Статический вывод типа выражения."""
        if isinstance(expr, Literal):
            if expr.lit_type == 'int':
                return 'целое'
            elif expr.lit_type == 'float':
                return 'дробь'
            elif expr.lit_type == 'string':
                return 'текст'
            elif expr.lit_type == 'bool':
                return 'логика'
            elif expr.lit_type == 'null':
                return 'пусто'
        elif isinstance(expr, Identifier):
            info = self.current_scope.resolve_var(expr.name)
            if info and info.type_ann:
                return info.type_ann.name
        elif isinstance(expr, BinaryOp):
            left = self._infer_type(expr.left)
            right = self._infer_type(expr.right)
            if left and right:
                if expr.operator in ('+', '-', '*', '/', '%'):
                    if left == 'дробь' or right == 'дробь':
                        return 'дробь'
                    return 'целое'
                if expr.operator in ('==', '!=', '<', '>', '<=', '>='):
                    return 'логика'
        elif isinstance(expr, CallExpr):
            # Не знаем тип возвращаемого значения без анализа функции
            pass
        return None
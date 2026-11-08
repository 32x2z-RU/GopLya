# Интерпретатор (tree-walking)

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, Generator
import sys
import traceback

from .ast import *
from .tokens import TokenType
from .messages import error_msg, warning_msg, runtime_msg
from .runtime.values import (
    GopValue, IntValue, FloatValue, StringValue, BoolValue, NULL,
    ListValue, DictValue, FunctionValue, GopInstance, GonecValue,
    GopClass, Environment, to_gop_value
)
from .runtime.errors import Kosyak, BumperKosyak, BufferFullKosyak, TypeKosyak, IndexKosyak
from .runtime.eventloop import get_event_loop, EventLoop
from .runtime.events import slushai, kin_klich, otstan
from .runtime.buffers import new_buffera, new_vot_eto_buffera, Buffer
from .runtime.streams import new_sizhka, SIGARA, PAPIROSKA, Sizhka
from .runtime.dvornik import Dvornik
from .stdlib import get_module, is_builtin
from .analyzer import AnalysisError


class ReturnException(Exception):
    def __init__(self, value: GopValue):
        self.value = value
        super().__init__()


class BreakException(Exception):
    pass


class ContinueException(Exception):
    pass


class NaPotomException(Exception):
    """Специальное исключение для выполнения на_потом при ошибке."""
    def __init__(self, statement: Statement):
        self.statement = statement
        super().__init__()


class Interpreter:
    """Дерево-обходной интерпретатор."""
    
    def __init__(self, program: Program, virtual_time: bool = False, network_allowed: bool = False):
        self.program = program
        self.global_env = Environment()
        self.current_env = self.global_env
        self.virtual_time = virtual_time
        self.network_allowed = network_allowed
        self.event_loop = EventLoop(virtual_time)
        self.call_stack: List[Dict[str, Any]] = []  # для трассировки
        
        # Инициализация встроенных модулей
        self._init_builtins()
    
    def _init_builtins(self):
        """Инициализирует встроенные имена в глобальном окружении."""
        # Базовые значения
        self.global_env.define('пусто', NULL, is_const=True)
        self.global_env.define('правда', BoolValue(True), is_const=True)
        self.global_env.define('неправда', BoolValue(False), is_const=True)
        
        # Конструкторы косяков
        from .runtime.errors import Kosyak, BumperKosyak
        self.global_env.define('Косяк', FunctionValue('Косяк', [], None, None, False, False, line=0), is_const=True)
        self.global_env.define('БамперКосяк', FunctionValue('БамперКосяк', [], None, None, False, False, line=0), is_const=True)
        
        # Классы буферов и сижек
        self.global_env.define('Буфера', FunctionValue('Буфера', [], None, None, False, False, line=0), is_const=True)
        self.global_env.define('Вот_это_буфера', FunctionValue('Вот_это_буфера', [], None, None, False, False, line=0), is_const=True)
        self.global_env.define('Сижка', FunctionValue('Сижка', [], None, None, False, False, line=0), is_const=True)
        self.global_env.define('сигара', SIGARA, is_const=True)
        self.global_env.define('папироска', PAPIROSKA, is_const=True)
        
        # Гонец и братва
        self.global_env.define('Гонец', FunctionValue('Гонец', [], None, None, False, False, line=0), is_const=True)
        self.global_env.define('братва', FunctionValue('братва', [], None, None, False, False, line=0), is_const=True)
        
        # Дворник
        self.global_env.define('Дворник', Dvornik, is_const=True)
        
        # Функции Версаль (автоматически доступны)
        from .stdlib.versailles import get_exports as versailles_exports
        for name, func in versailles_exports().items():
            self.global_env.define(name, FunctionValue(name, [], None, None, False, False, line=0), is_const=True)
    
    def run(self) -> int:
        """Запускает программу. Возвращает код выхода."""
        # Настраиваем систему событий
        from .runtime.events import get_event_system
        get_event_system().set_interpreter(self)
        
        try:
            # Выполняем все объявления верхнего уровня
            for decl in self.program.declarations:
                self._execute_declaration(decl)
            
            # Ждём завершения всех асинхронных задач
            self.event_loop.run_until_complete()
            
            # Проверка утечек шухер
            if self.event_loop.check_shukher_leaks():
                print(warning_msg("W003", 0), file=sys.stderr)
            
            return 0
            
        except Kosyak as e:
            # Неперехваченный косяк
            stack_trace = self._format_stack_trace()
            print(runtime_msg("R001", message=e.message), file=sys.stderr)
            for frame in stack_trace:
                print(f"  в кортане «{frame['function']}», строка {frame['line']}", file=sys.stderr)
            return 13
        except Exception as e:
            # Внутренняя ошибка интерпретатора (баг)
            print(f"Внутренняя ошибка интерпретатора: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return 1
    
    def _format_stack_trace(self) -> List[Dict[str, Any]]:
        """Форматирует стек вызовов."""
        frames = []
        for frame in reversed(self.call_stack):
            frames.append({'function': frame.get('function', '?'), 'line': frame.get('line', 0)})
        return frames
    
    def _push_call(self, function: str, line: int):
        self.call_stack.append({'function': function, 'line': line})
    
    def _pop_call(self):
        if self.call_stack:
            self.call_stack.pop()
    
    # --- Выполнение объявлений ---
    
    def _execute_declaration(self, decl: Declaration):
        if isinstance(decl, PivasDecl):
            value = self._eval_expression(decl.value)
            self.current_env.define(decl.name, value, is_const=True)
        elif isinstance(decl, SemkaDecl):
            value = self._eval_expression(decl.value) if decl.value else NULL
            self.current_env.define(decl.name, value, is_const=False)
        elif isinstance(decl, KortanDecl):
            func = FunctionValue(
                decl.name, decl.params, decl.body, self.current_env,
                decl.is_async, decl.is_strict, decl.return_type, decl.line()
            )
            self.current_env.define(decl.name, func, is_const=True)
        elif isinstance(decl, GopDecl):
            self._create_gop_class(decl)
        elif isinstance(decl, DogovornyakDecl):
            pass  # Интерфейсы проверяются на этапе анализа
        elif isinstance(decl, PozvatDecl):
            self._import_module(decl)
        elif isinstance(decl, Statement):
            self._execute_statement(decl)
    
    def _create_gop_class(self, decl: GopDecl):
        """Создаёт класс гопа."""
        # Родитель
        parent_class = None
        if decl.parent:
            parent_class = self.current_env.get(decl.parent)
            if not isinstance(parent_class, GopClass):
                raise Kosyak(f"Родитель «{decl.parent}» не является гопом")
        
        # Поля
        fields = {}
        for member in decl.members:
            if member.field:
                fields[member.field.name] = member.field
        
        # Методы
        methods = {}
        modifiers = {}
        for member in decl.members:
            if member.method:
                method_func = FunctionValue(
                    member.method.name, member.method.params, member.method.body,
                    self.current_env, member.method.is_async, member.method.is_strict,
                    member.method.return_type, member.method.line()
                )
                methods[member.method.name] = method_func
            if member.field:
                modifiers[member.field.name] = member.modifier or 'у_подъезда'
            if member.method:
                modifiers[member.method.name] = member.modifier or 'у_подъезда'
        
        gop_class = GopClass(
            decl.name, parent_class, decl.interfaces,
            fields, methods, modifiers, decl.is_strict
        )
        self.current_env.define(decl.name, gop_class, is_const=True)
    
    def _import_module(self, decl: PozvatDecl):
        """Импортирует модуль."""
        module_name = decl.module
        
        if is_builtin(module_name):
            exports = get_module(module_name)
            if decl.names:
                # Выборочный импорт
                for name in decl.names:
                    if name in exports:
                        if decl.alias:
                            self.current_env.define(f"{decl.alias}.{name}", exports[name], is_const=True)
                        else:
                            self.current_env.define(name, exports[name], is_const=True)
            else:
                # Полный импорт
                if decl.alias:
                    # Через псевдоним
                    for name, value in exports.items():
                        self.current_env.define(f"{decl.alias}.{name}", value, is_const=True)
                else:
                    # Напрямую
                    for name, value in exports.items():
                        self.current_env.define(name, value, is_const=True)
        else:
            # Пользовательский модуль — пока заглушка
            pass
    
    # --- Выполнение операторов ---
    
    def _execute_statement(self, stmt: Statement):
        if isinstance(stmt, Block):
            prev_env = self.current_env
            self.current_env = Environment(parent=prev_env)
            try:
                for s in stmt.statements:
                    self._execute_statement(s)
            finally:
                self.current_env = prev_env
        
        elif isinstance(stmt, IfStmt):
            cond = self._eval_expression(stmt.condition)
            if self._is_truthy(cond):
                self._execute_statement(stmt.then_block)
            else:
                executed = False
                for elif_cond, elif_block in stmt.elif_branches:
                    elif_val = self._eval_expression(elif_cond)
                    if self._is_truthy(elif_val):
                        self._execute_statement(elif_block)
                        executed = True
                        break
                if not executed and stmt.else_block:
                    self._execute_statement(stmt.else_block)
        
        elif isinstance(stmt, WhileStmt):
            while True:
                cond = self._eval_expression(stmt.condition)
                if not self._is_truthy(cond):
                    break
                try:
                    self._execute_statement(stmt.body)
                except BreakException:
                    break
                except ContinueException:
                    continue
        
        elif isinstance(stmt, ForStmt):
            if stmt.iterable:
                # По коллекции
                iterable_val = self._eval_expression(stmt.iterable)
                items = self._to_iterable(iterable_val)
                for item in items:
                    prev_env = self.current_env
                    self.current_env = Environment(parent=prev_env)
                    self.current_env.define(stmt.var_name, item)
                    try:
                        self._execute_statement(stmt.body)
                    except BreakException:
                        self.current_env = prev_env
                        break
                    except ContinueException:
                        self.current_env = prev_env
                        continue
                    self.current_env = prev_env
            else:
                # По диапазону
                start = self._eval_expression(stmt.range_start) if stmt.range_start else IntValue(0)
                end = self._eval_expression(stmt.range_end)
                
                if not isinstance(start, IntValue) or not isinstance(end, IntValue):
                    raise Kosyak("Диапазон работает только с целыми числами")
                
                step = 1
                if stmt.range_inclusive:
                    end_val = end.value + 1
                else:
                    end_val = end.value
                
                for i in range(start.value, end_val, step):
                    prev_env = self.current_env
                    self.current_env = Environment(parent=prev_env)
                    self.current_env.define(stmt.var_name, IntValue(i))
                    try:
                        self._execute_statement(stmt.body)
                    except BreakException:
                        self.current_env = prev_env
                        break
                    except ContinueException:
                        self.current_env = prev_env
                        continue
                    self.current_env = prev_env
        
        elif isinstance(stmt, TryStmt):
            try:
                self._execute_statement(stmt.try_block)
            except Kosyak as e:
                caught = False
                for catch in stmt.catch_blocks:
                    # Проверка типа (упрощённо - всегда ловим)
                    caught = True
                    prev_env = self.current_env
                    self.current_env = Environment(parent=prev_env)
                    # Сохраняем сам объект исключения, а не строку
                    self.current_env.define(catch.var_name, e)
                    self._execute_statement(catch.block)
                    self.current_env = prev_env
                    break
                if not caught:
                    raise
            finally:
                if stmt.finally_block:
                    self._execute_statement(stmt.finally_block)
        
        elif isinstance(stmt, PivasDecl):
            value = self._eval_expression(stmt.value)
            self.current_env.define(stmt.name, value, is_const=True)
        
        elif isinstance(stmt, SemkaDecl):
            value = self._eval_expression(stmt.value) if stmt.value else NULL
            self.current_env.define(stmt.name, value, is_const=False)
        
        elif isinstance(stmt, NaPotomStmt):
            self.current_env.add_deferred(stmt)
        
        elif isinstance(stmt, ReturnStmt):
            value = self._eval_expression(stmt.value) if stmt.value else NULL
            raise ReturnException(value)
        
        elif isinstance(stmt, ThrowStmt):
            value = self._eval_expression(stmt.value)
            if not isinstance(value, Kosyak):
                raise Kosyak("Кидать можно только Косяк")
            raise value
        
        elif isinstance(stmt, BreakStmt):
            raise BreakException()
        
        elif isinstance(stmt, ContinueStmt):
            raise ContinueException()
        
        elif isinstance(stmt, BazarStmt):
            args = [self._eval_expression(arg) for arg in stmt.args]
            output = " ".join(arg.to_display() for arg in args)
            print(output)
        
        elif isinstance(stmt, AssignStmt):
            target = stmt.target
            value = self._eval_expression(stmt.value)
            
            if isinstance(target, Identifier):
                if not self.current_env.assign(target.name, value):
                    raise Kosyak(error_msg("E003", stmt.line()))
            elif isinstance(target, MemberExpr):
                obj = self._eval_expression(target.object)
                if isinstance(obj, GopInstance):
                    modifier = obj.class_def.modifiers.get(target.name, 'у_подъезда')
                    if modifier == 'за_гаражами':
                        raise Kosyak(runtime_msg("R006"))
                    obj.fields[target.name] = value
                elif isinstance(obj, DictValue):
                    obj.items[target.name] = value
                else:
                    raise Kosyak("Нельзя присваивать полю не-объекта")
            elif isinstance(target, IndexExpr):
                obj = self._eval_expression(target.object)
                index = self._eval_expression(target.index)
                if isinstance(obj, ListValue):
                    if not isinstance(index, IntValue):
                        raise Kosyak("Индекс должен быть целым числом")
                    if index.value < 0 or index.value >= len(obj.elements):
                        raise IndexKosyak(runtime_msg("R007"))
                    obj.elements[index.value] = value
                else:
                    raise Kosyak("Индексация поддерживается только для кучек")
            else:
                raise Kosyak("Недопустимая цель присваивания")
        
        elif isinstance(stmt, ExpressionStmt):
            self._eval_expression(stmt.expression)
        
        elif isinstance(stmt, SlushaiStmt):
            handler = self._eval_expression(stmt.handler)
            slushai(stmt.event_name, handler)
        
        elif isinstance(stmt, KinKlichStmt):
            args = [self._eval_expression(arg) for arg in stmt.args]
            kin_klich(stmt.event_name, args)
        
        elif isinstance(stmt, OtstanStmt):
            otstan(stmt.event_name)
        
        elif isinstance(stmt, PoBratskiExpr):
            self._execute_po_bratski(stmt)
        
        else:
            pass
    
    def _execute_po_bratski(self, stmt: PoBratskiExpr):
        """Выполняет оператор по_братски."""
        source_val = self._eval_expression(stmt.source)
        
        # Получаем числовое значение источника
        if isinstance(source_val, (IntValue, FloatValue)):
            total = float(source_val.value) if isinstance(source_val, FloatValue) else source_val.value
        else:
            raise Kosyak("Источник для по_братски должен быть числом")
        
        # Вычисляем веса
        targets = []
        total_weight = 0
        for t in stmt.targets:
            weight = 1
            if t.weight:
                w_val = self._eval_expression(t.weight)
                if isinstance(w_val, (IntValue, FloatValue)):
                    weight = float(w_val.value) if isinstance(w_val, FloatValue) else w_val.value
            targets.append((t.target, weight))
            total_weight += weight
        
        if total_weight == 0:
            raise Kosyak("Нулевая сумма весов")
        
        # Проверка W002
        if total < len(targets) and all(isinstance(t[0], Identifier) for t in targets):
            # Только если цели — переменные (lvalue)
            print(warning_msg("W002", stmt.line()), file=sys.stderr)
        
        # Вычисляем доли
        is_float = isinstance(source_val, FloatValue)
        shares = []
        for target_expr, weight in targets:
            if is_float:
                share = total * weight / total_weight
            else:
                share = int(total * weight / total_weight)
            shares.append((target_expr, share))
        
        # Остаток первому (для целых)
        if not is_float:
            allocated = sum(s for _, s in shares)
            remainder = total - allocated
            if remainder > 0 and shares:
                shares[0] = (shares[0][0], shares[0][1] + remainder)
        
        # Применяем к целям (прибавляем к текущим значениям)
        for target_expr, share in shares:
            if isinstance(target_expr, Identifier):
                current = self.current_env.get(target_expr.name)
                if current is None:
                    current = IntValue(0) if not is_float else FloatValue(0.0)
                if isinstance(current, IntValue) and not is_float:
                    new_val = current.value + share
                    self.current_env.assign(target_expr.name, IntValue(new_val))
                elif isinstance(current, FloatValue) or is_float:
                    new_val = float(current.value) + share
                    self.current_env.assign(target_expr.name, FloatValue(new_val))
                else:
                    raise TypeKosyak("Цель должна быть числом")
            elif isinstance(target_expr, MemberExpr):
                obj = self._eval_expression(target_expr.object)
                if isinstance(obj, GopInstance):
                    current = obj.fields.get(target_expr.name, IntValue(0))
                    if isinstance(current, IntValue) and not is_float:
                        obj.fields[target_expr.name] = IntValue(current.value + share)
                    elif isinstance(current, FloatValue) or is_float:
                        obj.fields[target_expr.name] = FloatValue(float(current.value) + share)
                    else:
                        raise TypeKosyak("Цель должна быть числом")
                else:
                    raise Kosyak("Цель должна быть переменной или полем")
            else:
                raise Kosyak("Цель должна быть переменной")
        
        # Обнуляем источник если это lvalue
        if isinstance(stmt.source, Identifier):
            self.current_env.assign(stmt.source.name, IntValue(0) if not is_float else FloatValue(0.0))
    
    def _to_iterable(self, value: GopValue) -> List[GopValue]:
        """Преобразует значение в итерируемую последовательность."""
        if isinstance(value, ListValue):
            return value.elements
        elif isinstance(value, DictValue):
            return [StringValue(k) for k in value.items.keys()]
        elif isinstance(value, StringValue):
            return [StringValue(ch) for ch in value.value]
        elif isinstance(value, Buffer):
            return value._data
        elif isinstance(value, type) and hasattr(value, '__iter__'):
            return list(value)
        else:
            raise Kosyak("Нельзя итерировать по этому значению")
    
    # --- Вычисление выражений ---
    
    def _eval_expression(self, expr: Expression) -> GopValue:
        if isinstance(expr, Literal):
            return self._eval_literal(expr)
        elif isinstance(expr, Identifier):
            val = self.current_env.get(expr.name)
            if val is None:
                raise Kosyak(f"Кто такой «{expr.name}»? Я его не знаю.")
            return val
        elif isinstance(expr, SelfExpr):
            # self должен быть в окружении
            val = self.current_env.get('сам')
            if val is None:
                raise Kosyak("сам недоступен вне гопа")
            return val
        elif isinstance(expr, BatyaExpr):
            val = self.current_env.get('батя')
            if val is None:
                raise Kosyak("батя недоступен")
            return val
        elif isinstance(expr, BinaryOp):
            return self._eval_binary_op(expr)
        elif isinstance(expr, UnaryOp):
            return self._eval_unary_op(expr)
        elif isinstance(expr, TernaryOp):
            cond = self._eval_expression(expr.condition)
            if self._is_truthy(cond):
                return self._eval_expression(expr.then_expr)
            else:
                return self._eval_expression(expr.else_expr)
        elif isinstance(expr, CallExpr):
            return self._eval_call(expr)
        elif isinstance(expr, IndexExpr):
            return self._eval_index(expr)
        elif isinstance(expr, MemberExpr):
            return self._eval_member(expr)
        elif isinstance(expr, NewExpr):
            return self._eval_new(expr)
        elif isinstance(expr, ListLiteral):
            elements = [self._eval_expression(e) for e in expr.elements]
            return ListValue(elements)
        elif isinstance(expr, DictLiteral):
            items = {}
            for k, v in expr.entries:
                key_val = self._eval_expression(k)
                val = self._eval_expression(v)
                if isinstance(key_val, StringValue):
                    items[key_val.value] = val
                else:
                    items[key_val.to_display()] = val
            return DictValue(items)
        elif isinstance(expr, Interpolation):
            parts = []
            for part in expr.parts:
                if isinstance(part, str):
                    parts.append(part)
                else:
                    val = self._eval_expression(part)
                    parts.append(val.to_display())
            return StringValue("".join(parts))
        elif isinstance(expr, LambdaExpr):
            return FunctionValue(
                "", expr.params, expr.body, self.current_env, expr.is_async, line=expr.line()
            )
        elif isinstance(expr, PoBratskiExpr):
            # по_братски как выражение не должно использоваться, только как оператор
            self._execute_po_bratski(expr)
            return NULL
        else:
            raise Kosyak(f"Неизвестное выражение: {type(expr)}")
    
    def _eval_literal(self, expr: Literal) -> GopValue:
        if expr.lit_type == 'int':
            return IntValue(expr.value)
        elif expr.lit_type == 'float':
            return FloatValue(expr.value)
        elif expr.lit_type == 'string':
            return StringValue(expr.value)
        elif expr.lit_type == 'bool':
            return BoolValue(expr.value)
        elif expr.lit_type == 'null':
            return NULL
        raise Kosyak(f"Неизвестный литерал: {expr.lit_type}")
    
    def _eval_binary_op(self, expr: BinaryOp) -> GopValue:
        left = self._eval_expression(expr.left)
        right = self._eval_expression(expr.right)
        op = expr.operator
        
        # Арифметика
        if op in ('+', '-', '*', '/', '%', '**'):
            return self._arithmetic(left, right, op)
        
        # Сравнение
        if op in ('==', '!='):
            return BoolValue(self._equal(left, right) if op == '==' else not self._equal(left, right))
        if op in ('<', '>', '<=', '>='):
            return BoolValue(self._compare(left, right, op))
        
        # Логика
        if op in ('&&', 'и_ещё'):
            return BoolValue(self._is_truthy(left) and self._is_truthy(right))
        if op in ('||', 'или_чё'):
            return BoolValue(self._is_truthy(left) or self._is_truthy(right))
        if op == '??':
            return right if isinstance(left, NullValue) else left
        
        raise Kosyak(f"Неизвестный бинарный оператор: {op}")
    
    def _arithmetic(self, left: GopValue, right: GopValue, op: str) -> GopValue:
        # Числа
        if isinstance(left, (IntValue, FloatValue)) and isinstance(right, (IntValue, FloatValue)):
            l = float(left.value) if isinstance(left, FloatValue) else left.value
            r = float(right.value) if isinstance(right, FloatValue) else right.value
            
            if op == '+':
                result = l + r
            elif op == '-':
                result = l - r
            elif op == '*':
                result = l * r
            elif op == '/':
                if r == 0:
                    raise Kosyak(runtime_msg("R005"))
                result = l / r
            elif op == '%':
                if r == 0:
                    raise Kosyak(runtime_msg("R005"))
                result = l % r
            elif op == '**':
                result = l ** r
            
            # Возвращаем тип
            if isinstance(left, FloatValue) or isinstance(right, FloatValue) or op == '/':
                return FloatValue(result)
            return IntValue(int(result))
        
        # Строки: конкатенация
        if op == '+' and isinstance(left, StringValue):
            return left + right  # StringValue.__add__ делает приведение
        
        raise Kosyak(f"Оператор {op} не применим к этим типам")
    
    def _equal(self, left: GopValue, right: GopValue) -> bool:
        if isinstance(left, (IntValue, FloatValue)) and isinstance(right, (IntValue, FloatValue)):
            return float(left.value) == float(right.value)
        if type(left) != type(right):
            return False
        return left == right
    
    def _compare(self, left: GopValue, right: GopValue, op: str) -> bool:
        if isinstance(left, (IntValue, FloatValue)) and isinstance(right, (IntValue, FloatValue)):
            l = float(left.value) if isinstance(left, FloatValue) else left.value
            r = float(right.value) if isinstance(right, FloatValue) else right.value
            if op == '<': return l < r
            if op == '>': return l > r
            if op == '<=': return l <= r
            if op == '>=': return l >= r
        if isinstance(left, StringValue) and isinstance(right, StringValue):
            if op == '<': return left.value < right.value
            if op == '>': return left.value > right.value
            if op == '<=': return left.value <= right.value
            if op == '>=': return left.value >= right.value
        raise Kosyak(f"Нельзя сравнивать {left.gop_type_name()} и {right.gop_type_name()}")
    
    def _eval_unary_op(self, expr: UnaryOp) -> GopValue:
        operand = self._eval_expression(expr.operand)
        op = expr.operator
        
        if op == '-':
            if isinstance(operand, (IntValue, FloatValue)):
                val = -operand.value
                return FloatValue(val) if isinstance(operand, FloatValue) else IntValue(val)
        elif op in ('!', 'не_а'):
            return BoolValue(not self._is_truthy(operand))
        elif op == 'подожди_пивас':
            # Ожидание гонца
            if isinstance(operand, GonecValue):
                # В синхронном контексте не можем ждать, возвращаем как есть
                # Настоящее ожидание происходит в async кортинах через event loop
                return operand
            return operand
        
        raise Kosyak(f"Неизвестный унарный оператор: {op}")
    
    def _eval_call(self, expr: CallExpr) -> GopValue:
        callee = self._eval_expression(expr.callee)
        args = []
        kwargs = {}
        
        for arg in expr.args:
            val = self._eval_expression(arg.value)
            if arg.name:
                kwargs[arg.name] = val
            else:
                args.append(val)
        
        # Встроенные функции
        if isinstance(callee, FunctionValue) and callee.name in ('базарь', 'перекур', 'шухер', 'отбой', 
                                                                 'дели_целиком', 'спроси', 'корень', 
                                                                 'округли', 'модуль', 'в_текст',
                                                                 'прочитай', 'запиши', 'есть',
                                                                 'достань', 'случайное', 'выбери', 'зерно',
                                                                 'сейчас', 'сегодня'):
            return self._call_builtin(callee.name, args, kwargs)
        
        # Пользовательская функция
        if isinstance(callee, FunctionValue):
            return self._call_function(callee, args, kwargs)
        
        # Bound methods (буферы, списки, Дворник и т.д.)
        if hasattr(callee, '__call__') and callable(callee):
            return callee(*args, **kwargs)
        
        # Конструктор гопа
        if isinstance(callee, GopClass):
            return self._construct_gop(callee, args, kwargs)
        
        # Конструкторы буферов/сижек
        if callee is Buffer or callee is Buffer.__name__:
            pass
        
        raise Kosyak(f"Нельзя вызывать {callee}")
    
    def _call_builtin(self, name: str, args: List[GopValue], kwargs: Dict[str, GopValue]) -> GopValue:
        """Вызывает встроенную функцию."""
        if name == 'базарь':
            output = " ".join(arg.to_display() for arg in args)
            print(output)
            return NULL
        
        elif name == 'перекур':
            # Возвращаем гонец
            sec = args[0] if args else IntValue(0)
            return self.event_loop.create_task(self._perekur_coro(sec))
        
        elif name == 'шухер':
            if args:
                self.event_loop.shukher(args[0])
            else:
                self.event_loop.shukher_all()
            return NULL
        
        elif name == 'отбой':
            if args:
                self.event_loop.otboi(args[0])
            else:
                self.event_loop.otboi_all()
            return NULL
        
        elif name == 'дели_целиком':
            a, b = args[0], args[1]
            if isinstance(a, (IntValue, FloatValue)) and isinstance(b, (IntValue, FloatValue)):
                a_val = int(a.value) if isinstance(a, FloatValue) else a.value
                b_val = int(b.value) if isinstance(b, FloatValue) else b.value
                if b_val == 0:
                    raise Kosyak(runtime_msg("R005"))
                return IntValue(a_val // b_val)
            raise Kosyak("Аргументы должны быть числами")
        
        elif name == 'спроси':
            prompt = args[0] if args else NULL
            if prompt is not NULL:
                print(prompt.to_display(), end="", flush=True)
            line = sys.stdin.readline()
            if line.endswith('\n'):
                line = line[:-1]
            return StringValue(line)
        
        elif name == 'корень':
            x = args[0]
            if isinstance(x, (IntValue, FloatValue)):
                import math
                val = float(x.value)
                if val < 0:
                    raise Kosyak("Корень из отрицательного")
                return FloatValue(math.sqrt(val))
            raise Kosyak("Аргумент должен быть числом")
        
        elif name == 'округли':
            x = args[0]
            places = args[1] if len(args) > 1 else IntValue(0)
            if isinstance(x, (IntValue, FloatValue)):
                val = float(x.value)
                p = int(places.value) if isinstance(places, IntValue) else 0
                rounded = round(val, p)
                if p == 0:
                    return IntValue(int(rounded))
                return FloatValue(rounded)
            raise Kosyak("Аргумент должен быть числом")
        
        elif name == 'модуль':
            x = args[0]
            if isinstance(x, (IntValue, FloatValue)):
                val = abs(float(x.value))
                return IntValue(int(val)) if isinstance(x, IntValue) else FloatValue(val)
            raise Kosyak("Аргумент должен быть числом")
        
        elif name == 'в_текст':
            return StringValue(args[0].to_display())
        
        elif name == 'прочитай':
            path = args[0]
            if isinstance(path, StringValue):
                try:
                    with open(path.value, 'r', encoding='utf-8') as f:
                        return StringValue(f.read())
                except FileNotFoundError:
                    raise Kosyak(f"Файл не найден: {path.value}")
            raise Kosyak("Путь должен быть текстом")
        
        elif name == 'запиши':
            path, text = args[0], args[1]
            if isinstance(path, StringValue) and isinstance(text, StringValue):
                with open(path.value, 'w', encoding='utf-8') as f:
                    f.write(text.value)
                return NULL
            raise Kosyak("Путь и текст должны быть строками")
        
        elif name == 'есть':
            path = args[0]
            if isinstance(path, StringValue):
                import os
                return BoolValue(os.path.exists(path.value))
            raise Kosyak("Путь должен быть текстом")
        
        elif name == 'достань':
            url = args[0]
            if not self.network_allowed:
                raise Kosyak("Ларёк закрыт")
            if isinstance(url, StringValue):
                # Возвращаем гонец
                return self.event_loop.create_task(self._dostan_coro(url))
            raise Kosyak("URL должен быть текстом")
        
        elif name == 'случайное':
            ot, do = args[0], args[1]
            import random
            if isinstance(ot, IntValue) and isinstance(do, IntValue):
                return IntValue(random.randint(ot.value, do.value))
            if isinstance(ot, FloatValue) and isinstance(do, FloatValue):
                return FloatValue(random.uniform(ot.value, do.value))
            raise Kosyak("Аргументы должны быть числами")
        
        elif name == 'выбери':
            items = args[0]
            import random
            if isinstance(items, ListValue):
                if not items.elements:
                    raise Kosyak("Кучка пуста")
                return random.choice(items.elements)
            raise Kosyak("Аргумент должен быть кучкой")
        
        elif name == 'зерно':
            n = args[0]
            import random
            if isinstance(n, IntValue):
                random.seed(n.value)
                return NULL
            raise Kosyak("Зерно должно быть целым")
        
        elif name == 'сейчас':
            import time
            return FloatValue(time.time())
        
        elif name == 'сегодня':
            from datetime import datetime
            return StringValue(datetime.now().strftime("%Y-%m-%d"))
        
        return NULL
    
    def _perekur_coro(self, sec: GopValue) -> Generator[GonecValue, GopValue, GopValue]:
        sec_val = float(sec.value) if isinstance(sec, (IntValue, FloatValue)) else 0
        yield GonecValue()  # Заглушка для виртуального времени
        return NULL
    
    def _dostan_coro(self, url: StringValue) -> Generator[GonecValue, GopValue, GopValue]:
        import urllib.request
        yield GonecValue()
        try:
            req = urllib.request.Request(url.value, headers={'User-Agent': 'GopLya/2.2'})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8')
            return StringValue(content)
        except Exception as e:
            raise Kosyak(f"Ошибка сети: {e}")
    
    def _call_function(self, func: FunctionValue, args: List[GopValue], kwargs: Dict[str, GopValue]) -> GopValue:
        """Вызывает пользовательскую функцию."""
        if func.is_async:
            # Асинхронная функция — создаём корутину и возвращаем гонец
            return self.event_loop.create_task(self._run_function_coro(func, args, kwargs))
        else:
            # Синхронная — выполняем сразу
            return self._run_function_sync(func, args, kwargs)
    
    def _run_function_sync(self, func: FunctionValue, args: List[GopValue], kwargs: Dict[str, GopValue]) -> GopValue:
        """Выполняет синхронную функцию."""
        prev_env = self.current_env
        self.current_env = Environment(parent=func.closure)
        
        # Привязка параметров
        param_idx = 0
        for param in func.params:
            if param.name in kwargs:
                self.current_env.define(param.name, kwargs[param.name])
            elif param_idx < len(args):
                self.current_env.define(param.name, args[param_idx])
                param_idx += 1
            elif param.default:
                default_val = self._eval_expression(param.default)
                self.current_env.define(param.name, default_val)
            else:
                self.current_env.define(param.name, NULL)
        
        self._push_call(func.name, func.line())
        try:
            if isinstance(func.body, Block):
                for stmt in func.body.statements:
                    self._execute_statement(stmt)
                return NULL
            else:
                return self._eval_expression(func.body)
        except ReturnException as e:
            return e.value
        finally:
            self._pop_call()
            # Выполняем на_потом
            self.current_env.run_deferred(self)
            self.current_env = prev_env
    
    def _run_function_coro(self, func: FunctionValue, args: List[GopValue], kwargs: Dict[str, GopValue]) -> Generator[GonecValue, GopValue, GopValue]:
        """Корутина для асинхронной функции."""
        prev_env = self.current_env
        self.current_env = Environment(parent=func.closure)
        
        # Привязка параметров
        param_idx = 0
        for param in func.params:
            if param.name in kwargs:
                self.current_env.define(param.name, kwargs[param.name])
            elif param_idx < len(args):
                self.current_env.define(param.name, args[param_idx])
                param_idx += 1
            elif param.default:
                default_val = self._eval_expression(param.default)
                self.current_env.define(param.name, default_val)
            else:
                self.current_env.define(param.name, NULL)
        
        self._push_call(func.name, func.line())
        try:
            if isinstance(func.body, Block):
                for stmt in func.body.statements:
                    self._execute_statement(stmt)
                yield NULL
            else:
                result = self._eval_expression(func.body)
                yield result
        except ReturnException as e:
            yield e.value
        except Kosyak as e:
            raise e
        finally:
            self._pop_call()
            self.current_env.run_deferred(self)
            self.current_env = prev_env
    
    def _construct_gop(self, gop_class: GopClass, args: List[GopValue], kwargs: Dict[str, GopValue]) -> GopInstance:
        """Создаёт экземпляр гопа."""
        # Поля
        fields = {}
        
        # Инициализация полей родителя
        if gop_class.parent:
            parent_instance = self._construct_gop(gop_class.parent, args, kwargs)
            fields.update(parent_instance.fields)
        
        # Собственные поля с инициализаторами
        for name, field_decl in gop_class.fields.items():
            if field_decl.value:
                fields[name] = self._eval_expression(field_decl.value)
            else:
                fields[name] = NULL
        
        instance = GopInstance(gop_class, fields)
        
        # Конструктор
        constructor = gop_class.methods.get(gop_class.name)
        if constructor:
            # Подготовка аргументов для конструктора
            ctor_args = args
            ctor_kwargs = kwargs
            self._call_method(instance, constructor, ctor_args, ctor_kwargs)
        
        return instance
    
    def _call_method(self, instance: GopInstance, method: FunctionValue, args: List[GopValue], kwargs: Dict[str, GopValue]) -> GopValue:
        """Вызывает метод объекта."""
        prev_env = self.current_env
        self.current_env = Environment(parent=method.closure)
        
        # Привязка self
        self.current_env.define('сам', instance)
        
        # Привязка батя (родительский класс)
        if instance.class_def.parent:
            # Создаём прокси для батя
            self.current_env.define('батя', BatyaProxy(instance, instance.class_def.parent))
        
        # Параметры
        param_idx = 0
        for param in method.params:
            if param.name in kwargs:
                self.current_env.define(param.name, kwargs[param.name])
            elif param_idx < len(args):
                self.current_env.define(param.name, args[param_idx])
                param_idx += 1
            elif param.default:
                default_val = self._eval_expression(param.default)
                self.current_env.define(param.name, default_val)
            else:
                self.current_env.define(param.name, NULL)
        
        self._push_call(method.name, method.line())
        try:
            if isinstance(method.body, Block):
                for stmt in method.body.statements:
                    self._execute_statement(stmt)
                return NULL
            else:
                return self._eval_expression(method.body)
        except ReturnException as e:
            return e.value
        finally:
            self._pop_call()
            self.current_env.run_deferred(self)
            self.current_env = prev_env
    
    def _eval_index(self, expr: IndexExpr) -> GopValue:
        obj = self._eval_expression(expr.object)
        index = self._eval_expression(expr.index)
        
        if isinstance(obj, ListValue):
            if not isinstance(index, IntValue):
                raise Kosyak("Индекс должен быть целым числом")
            if index.value < 0 or index.value >= len(obj.elements):
                raise IndexKosyak(runtime_msg("R007"))
            return obj.elements[index.value]
        
        if isinstance(obj, DictValue):
            key = index.to_display()
            return obj.items.get(key, NULL)
        
        if isinstance(obj, StringValue):
            if not isinstance(index, IntValue):
                raise Kosyak("Индекс должен быть целым числом")
            if index.value < 0 or index.value >= len(obj.value):
                raise IndexKosyak(runtime_msg("R007"))
            return StringValue(obj.value[index.value])
        
        if isinstance(obj, Buffer):
            if not isinstance(index, IntValue):
                raise Kosyak("Индекс должен быть целым числом")
            if index.value < 0 or index.value >= len(obj._data):
                raise IndexKosyak(runtime_msg("R007"))
            return obj._data[index.value]
        
        raise Kosyak(f"Нельзя индексировать {obj.gop_type_name()}")
    
    def _eval_member(self, expr: MemberExpr) -> GopValue:
        obj = self._eval_expression(expr.object)
        
        if isinstance(obj, GopInstance):
            # Проверка доступа
            modifier = obj.class_def.modifiers.get(expr.name, 'у_подъезда')
            if modifier == 'за_гаражами':
                # Проверяем, вызываем ли мы из того же класса
                # Упрощённо: если safe navigation, возвращаем NULL
                if expr.safe:
                    return NULL
                raise Kosyak(runtime_msg(R006))
            
            # Поле
            if expr.name in obj.fields:
                return obj.fields[expr.name]
            
            # Метод
            if expr.name in obj.class_def.methods:
                method = obj.class_def.methods[expr.name]
                return BoundMethod(instance=obj, method=method)
            
            if expr.safe:
                return NULL
            raise Kosyak(f"Нет такого поля или метода: {expr.name}")
        
        elif isinstance(obj, DictValue):
            val = obj.items.get(expr.name)
            if val is None and expr.safe:
                return NULL
            return val or NULL
        
        elif isinstance(obj, ListValue):
            if expr.name == 'длина':
                return IntValue(len(obj.elements))
            # Методы кучки
            if expr.name == 'добавь':
                return BoundMethodList(obj, 'добавить')
            if expr.name == 'выкини':
                return BoundMethodList(obj, 'выкинуть')
            if expr.name == 'перемешай':
                return BoundMethodList(obj, 'перемешать')
            if expr.name == 'самая_большая':
                return BoundMethodList(obj, 'самая_большая')
            if expr.name == 'отбери':
                return BoundMethodList(obj, 'отобрать')
            if expr.safe:
                return NULL
            raise Kosyak(f"У кучки нет «{expr.name}»")
        
        elif isinstance(obj, StringValue):
            if expr.name == 'длина':
                return IntValue(len(obj.value))
            if expr.safe:
                return NULL
            raise Kosyak(f"У текста нет «{expr.name}»")
        
        elif isinstance(obj, Buffer):
            if expr.name == 'ёмкость':
                return IntValue(obj.capacity)
            if expr.name == 'длина':
                return IntValue(obj.length)
            if expr.name == 'положи':
                return BoundMethodBuffer(obj)
            if expr.name == 'всё':
                return BoundMethodBufferAll(obj)
            if expr.name == 'чёткий_бампер':
                return BoundMethodBufferBumper(obj)
            if expr.safe:
                return NULL
            raise Kosyak(f"У Буфера нет «{expr.name}»")
        
        elif isinstance(obj, Dvornik.__class__):
            if expr.name == 'подмети':
                return BoundMethodDvornikPodmeti()
            if expr.name == 'шелухи_в_куче':
                return BoundMethodDvornikSheluhi()
            if expr.safe:
                return NULL
            raise Kosyak(f"У Дворника нет «{expr.name}»")
        
        elif isinstance(obj, Kosyak):
            if expr.name == 'сообщение':
                from .runtime.values import StringValue as _StringValue
                return _StringValue(obj.message)
            if expr.safe:
                return NULL
            raise Kosyak(f"У косяка нет «{expr.name}»")
        
        elif isinstance(obj, Sizhka):
            if expr.name == 'бычок':
                from .runtime.values import BoolValue
                return BoolValue(obj.bychok)
            if expr.name == 'затянись':
                return BoundMethodSizhkaZatyanis(obj)
            if expr.name == 'возьми':
                return BoundMethodSizhkaVozmi(obj)
            if expr.safe:
                return NULL
            raise Kosyak(f"У Сижки нет «{expr.name}»")
        
        if expr.safe:
            return NULL
        raise Kosyak(f"Нельзя получить доступ к «{expr.name}» у {obj.gop_type_name()}")
    
    def _eval_new(self, expr: NewExpr) -> GopValue:
        if expr.class_name == 'Буфера':
            n = self._eval_expression(expr.args[0].value) if expr.args else IntValue(0)
            if isinstance(n, IntValue):
                buf = new_buffera(n.value, expr.is_ring)
                return to_gop_value(buf)
        elif expr.class_name == 'Вот_это_буфера':
            n = self._eval_expression(expr.args[0].value) if expr.args else IntValue(0)
            if isinstance(n, IntValue):
                buf = new_vot_eto_buffera(n.value, expr.is_ring)
                return to_gop_value(buf)
        elif expr.class_name == 'Сижка':
            kind = self._eval_expression(expr.args[0].value)
            source = self._eval_expression(expr.args[1].value)
            if isinstance(kind, StringValue):
                sizhka = new_sizhka(kind.value, source, self)
                return to_gop_value(sizhka)
        
        # Пользовательский гоп
        gop_class = self.current_env.get(expr.class_name)
        if isinstance(gop_class, GopClass):
            args = [arg.value for arg in expr.args]
            kwargs = {arg.name: arg.value for arg in expr.args if arg.name}
            return self._construct_gop(gop_class, args, kwargs)
        
        raise Kosyak(f"Неизвестный тип: {expr.class_name}")
    
    def _is_truthy(self, value: GopValue) -> bool:
        return value.is_truthy()


# Вспомогательные классы для привязанных методов

class BoundMethod:
    def __init__(self, instance: GopInstance, method: FunctionValue):
        self.instance = instance
        self.method = method
    
    def __call__(self, *args, **kwargs):
        # Вызывается через интерпретатор
        pass
    
    def to_display(self):
        return f"<метод {self.method.name}>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "кортан"


class BoundMethodList:
    def __init__(self, list_val: ListValue, name: str):
        self.list_val = list_val
        self.name = name
    
    def __call__(self, *args, **kwargs):
        if self.name == 'добавить':
            self.list_val.elements.append(args[0])
            return NULL
        elif self.name == 'выкинуть':
            idx = args[0].value if isinstance(args[0], IntValue) else 0
            if 0 <= idx < len(self.list_val.elements):
                return self.list_val.elements.pop(idx)
            raise Kosyak(runtime_msg("R007"))
        elif self.name == 'перемешать':
            import random
            random.shuffle(self.list_val.elements)
            return NULL
        elif self.name == 'самая_большая':
            if not self.list_val.elements:
                return NULL
            return max(self.list_val.elements, key=lambda x: float(x.value) if isinstance(x, (IntValue, FloatValue)) else 0)
        elif self.name == 'отобрать':
            func = args[0]
            result = []
            for item in self.list_val.elements:
                # Упрощённо: не можем вызвать функцию здесь
                pass
            return ListValue(result)
        return NULL
    
    def to_display(self):
        return f"<метод кучки {self.name}>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "кортан"


class BoundMethodBuffer:
    def __init__(self, buffer: Buffer):
        self.buffer = buffer
    
    def __call__(self, *args, **kwargs):
        self.buffer.put(args[0])
        return NULL
    
    def to_display(self):
        return "<метод Буфера положи>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "кортан"


class BoundMethodBufferAll:
    def __init__(self, buffer: Buffer):
        self.buffer = buffer
    
    def __call__(self, *args, **kwargs):
        return self.buffer.all()
    
    def to_display(self):
        return "<метод Буфера всё>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "кортан"


class BoundMethodBufferBumper:
    def __init__(self, buffer: Buffer):
        self.buffer = buffer
    
    def __call__(self, *args, **kwargs):
        if 'зад' in kwargs:
            k = kwargs['зад']
        elif args:
            k = args[0]
        else:
            raise Kosyak("нужен аргумент зад")
        if isinstance(k, IntValue):
            self.buffer.set_bumper(k.value)
        return NULL
    
    def to_display(self):
        return "<метод Буфера чёткий_бампер>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "кортан"


class BoundMethodDvornikPodmeti:
    def __call__(self, *args, **kwargs):
        Dvornik.podmeti()
        return NULL
    def to_display(self): return "<метод Дворник.подмети>"
    def is_truthy(self): return True
    def gop_type_name(self): return "кортан"


class BoundMethodDvornikSheluhi:
    def __call__(self, *args, **kwargs):
        return IntValue(Dvornik.sheluhi_v_kuche())
    def to_display(self): return "<метод Дворник.шелухи_в_куче>"
    def is_truthy(self): return True
    def gop_type_name(self): return "кортан"


class BoundMethodSizhkaZatyanis:
    def __init__(self, sizhka: Sizhka):
        self.sizhka = sizhka
    
    def __call__(self, *args, **kwargs):
        return self.sizhka.zatyanis()
    
    def to_display(self):
        return "<метод Сижки затянись>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "кортан"


class BoundMethodSizhkaVozmi:
    def __init__(self, sizhka: Sizhka):
        self.sizhka = sizhka
    
    def __call__(self, *args, **kwargs):
        if not args:
            raise Kosyak("возьми требует аргумент")
        n = args[0]
        if isinstance(n, IntValue):
            return self.sizhka.vozmi(n.value)
        raise Kosyak("Аргумент должен быть целым числом")
    
    def to_display(self):
        return "<метод Сижки возьми>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "кортан"


class BatyaProxy:
    """Прокси для вызова методов родителя через батя.метод()."""
    def __init__(self, instance: GopInstance, parent_class: GopClass):
        self.instance = instance
        self.parent_class = parent_class
    
    def __getattr__(self, name: str):
        method = self.parent_class.methods.get(name)
        if method:
            return BoundMethod(self.instance, method)
        raise AttributeError(f"У бати нет метода {name}")
    
    def __call__(self, *args, **kwargs):
        # Вызов конструктора родителя: батя(...)
        constructor = self.parent_class.methods.get(self.parent_class.name)
        if constructor:
            return BoundMethod(self.instance, constructor)(*args, **kwargs)
        raise Kosyak("У бати нет конструктора")
    
    def to_display(self):
        return "<батя>"
    
    def is_truthy(self):
        return True
    
    def gop_type_name(self):
        return "объект"

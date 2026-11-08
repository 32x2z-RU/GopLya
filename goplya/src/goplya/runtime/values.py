# Представление значений во время выполнения

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from ..ast import *


class GopValue:
    """Базовый класс для всех значений ГопЛи."""
    
    def to_display(self) -> str:
        """Форматирование для вывода (раздел 6.4 спецификации)."""
        raise NotImplementedError
    
    def is_truthy(self) -> bool:
        """Истинность в обычном режиме."""
        return True
    
    def gop_type_name(self) -> str:
        """Имя типа для сообщений об ошибках."""
        return "объект"


class IntValue(GopValue):
    def __init__(self, value: int):
        self.value = value
    
    def to_display(self) -> str:
        return str(self.value)
    
    def is_truthy(self) -> bool:
        return self.value != 0
    
    def gop_type_name(self) -> str:
        return "целое"
    
    def __eq__(self, other):
        if isinstance(other, IntValue):
            return self.value == other.value
        if isinstance(other, FloatValue):
            return self.value == other.value
        return False
    
    def __repr__(self):
        return f"IntValue({self.value})"


class FloatValue(GopValue):
    def __init__(self, value: float):
        self.value = value
    
    def to_display(self) -> str:
        # Целая дробь выводится как 1.0
        if self.value == int(self.value):
            return f"{self.value:.1f}"
        return str(self.value)
    
    def is_truthy(self) -> bool:
        return self.value != 0.0
    
    def gop_type_name(self) -> str:
        return "дробь"
    
    def __eq__(self, other):
        if isinstance(other, FloatValue):
            return self.value == other.value
        if isinstance(other, IntValue):
            return self.value == other.value
        return False
    
    def __repr__(self):
        return f"FloatValue({self.value})"


class StringValue(GopValue):
    def __init__(self, value: str):
        self.value = value
    
    def to_display(self) -> str:
        return self.value
    
    def is_truthy(self) -> bool:
        return self.value != ""
    
    def gop_type_name(self) -> str:
        return "текст"
    
    def __eq__(self, other):
        if isinstance(other, StringValue):
            return self.value == other.value
        return False
    
    def __add__(self, other):
        # Конкатенация строк (обычный режим)
        if isinstance(other, StringValue):
            return StringValue(self.value + other.value)
        return StringValue(self.value + other.to_display())
    
    def __repr__(self):
        return f"StringValue({self.value!r})"


class BoolValue(GopValue):
    def __init__(self, value: bool):
        self.value = value
    
    def to_display(self) -> str:
        return "правда" if self.value else "неправда"
    
    def is_truthy(self) -> bool:
        return self.value
    
    def gop_type_name(self) -> str:
        return "логика"
    
    def __eq__(self, other):
        if isinstance(other, BoolValue):
            return self.value == other.value
        return False
    
    def __repr__(self):
        return f"BoolValue({self.value})"


class NullValue(GopValue):
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        pass
    
    def to_display(self) -> str:
        return "пусто"
    
    def is_truthy(self) -> bool:
        return False
    
    def gop_type_name(self) -> str:
        return "пусто"
    
    def __eq__(self, other):
        return isinstance(other, NullValue)
    
    def __repr__(self):
        return "NullValue()"


NULL = NullValue()


class ListValue(GopValue):
    def __init__(self, elements: List[GopValue] = None):
        self.elements = elements or []
    
    def to_display(self) -> str:
        if not self.elements:
            return "[]"
        items = ", ".join(e.to_display() for e in self.elements)
        return f"[{items}]"
    
    def is_truthy(self) -> bool:
        return len(self.elements) > 0
    
    def gop_type_name(self) -> str:
        return "кучка"
    
    def __eq__(self, other):
        if isinstance(other, ListValue):
            return self.elements == other.elements
        return False
    
    def __repr__(self):
        return f"ListValue({self.elements})"


class DictValue(GopValue):
    def __init__(self, items: Dict[str, GopValue] = None):
        self.items = items or {}
    
    def to_display(self) -> str:
        if not self.items:
            return "{}"
        pairs = ", ".join(f"{k}: {v.to_display()}" for k, v in self.items.items())
        return f"{{{pairs}}}"
    
    def is_truthy(self) -> bool:
        return len(self.items) > 0
    
    def gop_type_name(self) -> str:
        return "общак"
    
    def __eq__(self, other):
        if isinstance(other, DictValue):
            return self.items == other.items
        return False
    
    def __repr__(self):
        return f"DictValue({self.items})"


class FunctionValue(GopValue):
    """Значение-функция (кортан или лямбда)."""
    
    def __init__(self, name: str, params: List[Parameter], body: Union[Block, Expression], 
                 closure: 'Environment', is_async: bool = False, is_strict: bool = False,
                 return_type: Optional[TypeAnn] = None, line: int = 0):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
        self.is_async = is_async
        self.is_strict = is_strict
        self.return_type = return_type
        self._line = line
    
    def line(self) -> int:
        return self._line
    
    def to_display(self) -> str:
        return f"<кортан {self.name}>" if self.name else "<кортан>"
    
    def is_truthy(self) -> bool:
        return True
    
    def gop_type_name(self) -> str:
        return "кортан"
    
    def __repr__(self):
        return f"FunctionValue({self.name}, async={self.is_async})"


class GopInstance(GopValue):
    """Экземпляр гопа (объект класса)."""
    
    def __init__(self, class_def: 'GopClass', fields: Dict[str, GopValue]):
        self.class_def = class_def
        self.fields = fields
    
    def to_display(self) -> str:
        return f"<{self.class_def.name}>"
    
    def is_truthy(self) -> bool:
        return True
    
    def gop_type_name(self) -> str:
        return self.class_def.name
    
    def __repr__(self):
        return f"GopInstance({self.class_def.name})"


class GonecValue(GopValue):
    """Гонец (Promise-like)."""
    
    def __init__(self):
        self._result: Optional[GopValue] = None
        self._error: Optional[BaseException] = None
        self._done = False
        self._callbacks: List[Callable[[GopValue], None]] = []
        self._error_callbacks: List[Callable[[BaseException], None]] = []
    
    def resolve(self, value: GopValue):
        self._result = value
        self._done = True
        for cb in self._callbacks:
            try:
                cb(value)
            except:
                pass
    
    def reject(self, error: BaseException):
        self._error = error
        self._done = True
        for cb in self._error_callbacks:
            try:
                cb(error)
            except:
                pass
    
    def then(self, callback: Callable[[GopValue], None]):
        if self._done:
            if self._error:
                pass  # ошибка уже обработана
            else:
                callback(self._result)
        else:
            self._callbacks.append(callback)
    
    def catch(self, callback: Callable[[BaseException], None]):
        if self._done and self._error:
            callback(self._error)
        else:
            self._error_callbacks.append(callback)
    
    def to_display(self) -> str:
        return "<гонец>"
    
    def is_truthy(self) -> bool:
        return True
    
    def gop_type_name(self) -> str:
        return "Гонец"
    
    def __repr__(self):
        return "GonecValue()"


class GopClass:
    """Определение класса (гопа)."""
    
    def __init__(self, name: str, parent: Optional['GopClass'], interfaces: List[str],
                 fields: Dict[str, FieldDecl], methods: Dict[str, FunctionValue],
                 modifiers: Dict[str, str], is_strict: bool):
        self.name = name
        self.parent = parent
        self.interfaces = interfaces
        self.fields = fields  # name -> FieldDecl
        self.methods = methods  # name -> FunctionValue
        self.modifiers = modifiers  # method/field name -> modifier
        self.is_strict = is_strict


class Environment:
    """Окружение (область видимости)."""
    
    def __init__(self, parent: Optional['Environment'] = None):
        self.parent = parent
        self.values: Dict[str, GopValue] = {}
        self.constants: set = set()  # имена пивас
        self.deferred: List[NaPotomStmt] = []  # на_потом для этого кортана
    
    def define(self, name: str, value: GopValue, is_const: bool = False):
        self.values[name] = value
        if is_const:
            self.constants.add(name)
    
    def assign(self, name: str, value: GopValue) -> bool:
        if name in self.values:
            if name in self.constants:
                return False  # ошибка: попытка изменить пивас
            self.values[name] = value
            return True
        if self.parent:
            return self.parent.assign(name, value)
        return False
    
    def get(self, name: str) -> Optional[GopValue]:
        if name in self.values:
            return self.values[name]
        if self.parent:
            return self.parent.get(name)
        return None
    
    def get_local(self, name: str) -> Optional[GopValue]:
        return self.values.get(name)
    
    def is_const(self, name: str) -> bool:
        if name in self.constants:
            return True
        if self.parent:
            return self.parent.is_const(name)
        return False
    
    def add_deferred(self, stmt: NaPotomStmt):
        self.deferred.append(stmt)
    
    def run_deferred(self, interpreter: 'Interpreter'):
        """Выполняет на_потом в обратном порядке (LIFO)."""
        for stmt in reversed(self.deferred):
            try:
                interpreter._execute_statement(stmt.statement)
            except Exception as e:
                # Ошибка в на_потом при уже летящем косяке заменяет его
                # (решение в DECISIONS.md)
                raise


# Вспомогательные функции для создания значений

def to_gop_value(value: Any) -> GopValue:
    """Преобразует Python-значение в GopValue."""
    if isinstance(value, bool):
        return BoolValue(value)
    elif isinstance(value, int):
        return IntValue(value)
    elif isinstance(value, float):
        return FloatValue(value)
    elif isinstance(value, str):
        return StringValue(value)
    elif value is None:
        return NULL
    elif isinstance(value, list):
        return ListValue([to_gop_value(v) for v in value])
    elif isinstance(value, dict):
        return DictValue({k: to_gop_value(v) for k, v in value.items()})
    else:
        return value  # уже GopValue


def from_gop_value(value: GopValue) -> Any:
    """Преобразует GopValue в Python-значение (для интероперабельности)."""
    if isinstance(value, (IntValue, FloatValue, StringValue, BoolValue)):
        return value.value
    elif isinstance(value, NullValue):
        return None
    elif isinstance(value, ListValue):
        return [from_gop_value(v) for v in value.elements]
    elif isinstance(value, DictValue):
        return {k: from_gop_value(v) for k, v in value.items()}
    else:
        return value
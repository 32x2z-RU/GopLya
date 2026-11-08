# Сижка (ленивые потоки)

from typing import Callable, List, Optional, Any, Iterator
from .values import GopValue, ListValue, FunctionValue, IntValue, StringValue
from .errors import Kosyak


class Sizhka(GopValue):
    """Ленивый поток значений."""
    
    def __init__(self, kind: str, source: Any, interpreter=None):
        """
        kind: 'сигара' (бесконечная) или 'папироска' (конечная)
        source: для сигары — кортан f(i), для папиросы — кучка
        interpreter: интерпретатор для вызова кортанов
        """
        self.kind = kind
        self.source = source
        self._index = 0
        self._cache: List[GopValue] = []
        self._exhausted = False
        self._interpreter = interpreter
    
    def set_interpreter(self, interpreter):
        self._interpreter = interpreter
    
    def to_display(self) -> str:
        return f"Сижка({self.kind})"
    
    def is_truthy(self) -> bool:
        return True
    
    def gop_type_name(self) -> str:
        return "Сижка"
    
    @property
    def bychok(self) -> bool:
        """True если поток иссяк (только для папироски)."""
        if self.kind == 'сигара':
            return False
        return self._exhausted
    
    def zatyanis(self) -> GopValue:
        """Следующее значение (затяжка)."""
        if self.kind == 'сигара':
            # Бесконечная: вызываем кортан с индексом
            if isinstance(self.source, FunctionValue) and self._interpreter:
                arg = IntValue(self._index)
                # Вызываем кортан через интерпретатор
                result = self._interpreter._call_function(self.source, [arg], {})
                self._index += 1
                return result
            else:
                raise Kosyak("Сигара требует кортан")
        
        else:  # папироска
            if self._exhausted:
                raise Kosyak("Бычок. Тянуть нечего.")
            
            if self._index < len(self._cache):
                val = self._cache[self._index]
                self._index += 1
                return val
            
            # Инициализируем из кучки если нужно
            if isinstance(self.source, ListValue) and not self._cache:
                self._cache = self.source.elements.copy()
            
            if self._index < len(self._cache):
                val = self._cache[self._index]
                self._index += 1
                if self._index >= len(self._cache):
                    self._exhausted = True
                return val
            
            self._exhausted = True
            raise Kosyak("Бычок. Тянуть нечего.")
    
    def vozmi(self, n: int) -> ListValue:
        """Взять следующие n значений."""
        result = []
        for _ in range(n):
            try:
                result.append(self.zatyanis())
            except Kosyak:
                break
        return ListValue(result)
    
    def __iter__(self) -> Iterator[GopValue]:
        if self.kind == 'сигара':
            # Бесконечный итератор
            while True:
                yield self.zatyanis()
        else:
            # Конечный
            while not self.bychok:
                yield self.zatyanis()
    
    def __repr__(self):
        return f"Sizhka({self.kind}, index={self._index}, exhausted={self._exhausted})"


# Константы-метки
SIGARA = "сигара"
PAPIROSKA = "папироска"


def new_sizhka(kind: str, source: Any, interpreter=None) -> Sizhka:
    """Создать новую Сижку."""
    return Sizhka(kind, source, interpreter)
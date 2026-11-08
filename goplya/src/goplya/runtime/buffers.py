# Буфера (Буфера, Вот_это_буфера, чёткий_бампер)

from typing import List, Optional, Any
from .errors import BufferFullKosyak, BumperKosyak, Kosyak
from .values import GopValue, ListValue


class Buffer:
    """Базовый класс буфера."""
    
    def __init__(self, capacity: int):
        self._capacity = capacity
        self._data: List[GopValue] = []
        self._is_ring = False
        self._bumper_limit: Optional[int] = None  # чёткий_бампер
    
    @property
    def capacity(self) -> int:
        return self._capacity
    
    @property
    def length(self) -> int:
        return len(self._data)
    
    @property
    def is_ring(self) -> bool:
        return self._is_ring
    
    def put(self, value: GopValue):
        """Положить значение в буфер."""
        # Проверка бампера
        if self._bumper_limit is not None:
            if self.length >= self._bumper_limit:
                raise BumperKosyak(f"Бабах! Чёткий бампер не пропустил: зад на позиции {self._bumper_limit}")
        
        if self._is_ring:
            # Кольцевой буфер: вытесняем старый
            if len(self._data) >= self._capacity:
                self._data.pop(0)
            self._data.append(value)
        else:
            # Обычный буфер: проверка переполнения
            if len(self._data) >= self._capacity:
                raise BufferFullKosyak("Буфера полная")
            self._data.append(value)
    
    def all(self) -> ListValue:
        """Вернуть все элементы от старого к новому."""
        return ListValue(self._data.copy())
    
    def set_ring(self):
        """Сделать буфер кольцевым."""
        self._is_ring = True
    
    def set_bumper(self, limit: int):
        """Установить чёткий бампер."""
        if self._is_ring:
            raise Kosyak("Кольцу бампер не нужен")
        if limit > self._capacity:
            limit = self._capacity
        self._bumper_limit = limit
    
    def __iter__(self):
        return iter(self._data)
    
    def __repr__(self):
        return f"Buffer(cap={self._capacity}, len={self.length}, ring={self._is_ring})"


class VotEtoBuffera(Buffer):
    """Вот_это_буфера — ёмкость 2*n."""
    
    def __init__(self, n: int):
        super().__init__(2 * n)


# Фабричные функции

def new_buffera(n: int, ring: bool = False) -> Buffer:
    """Создать новый Буфера."""
    buf = Buffer(n)
    if ring:
        buf.set_ring()
    return buf


def new_vot_eto_buffera(n: int, ring: bool = False) -> VotEtoBuffera:
    """Создать новый Вот_это_буфера."""
    buf = VotEtoBuffera(n)
    if ring:
        buf.set_ring()
    return buf
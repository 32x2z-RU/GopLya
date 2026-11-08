# Иерархия косяков (ошибок выполнения)

from typing import Optional
from ..messages import runtime_msg
from .values import GopValue, StringValue


class Kosyak(Exception, GopValue):
    """Базовый класс косяка (ошибки выполнения)."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
    
    def __str__(self):
        return self.message
    
    def to_display(self) -> str:
        return self.message
    
    def is_truthy(self) -> bool:
        return True
    
    def gop_type_name(self) -> str:
        return "Косяк"
    
    def __getattr__(self, name: str):
        if name == "сообщение":
            return StringValue(self.message)
        raise AttributeError(f"'Kosyak' object has no attribute '{name}'")


class BumperKosyak(Kosyak):
    """Косяк бампера буфера."""
    pass


class BufferFullKosyak(Kosyak):
    """Косяк переполнения буфера."""
    pass


class TypeKosyak(Kosyak):
    """Косяк несоответствия типов."""
    pass


class IndexKosyak(Kosyak):
    """Косяк выхода за границы индекса."""
    pass


class GopValue:
    """Минимальный заглушка для аннотаций типов."""
    pass


def format_unhandled_kosyak(kosyak: Kosyak, stack_trace: list = None) -> str:
    """Форматирует неперехваченный косяк для вывода в stderr."""
    lines = [runtime_msg("R001", message=kosyak.message)]
    if stack_trace:
        for frame in stack_trace:
            lines.append(f"  в кортане «{frame['function']}», строка {frame['line']}")
    return "\n".join(lines)


# Фабричные функции для стандартных косяков

def make_buffer_full() -> BufferFullKosyak:
    return BufferFullKosyak(runtime_msg("R002"))


def make_bumper_kosyak(k: int) -> BumperKosyak:
    return BumperKosyak(runtime_msg("R003", k=k))


def make_sizhka_exhausted() -> Kosyak:
    return Kosyak(runtime_msg("R004"))


def make_division_by_zero() -> Kosyak:
    return Kosyak(runtime_msg("R005"))


def make_private_access() -> Kosyak:
    return Kosyak(runtime_msg("R006"))


def make_index_out_of_bounds() -> IndexKosyak:
    return IndexKosyak(runtime_msg("R007"))


def make_type_mismatch(expected: str, got: str) -> TypeKosyak:
    return TypeKosyak(f"Тип не тот. Просили «{expected}», принесли «{got}».")
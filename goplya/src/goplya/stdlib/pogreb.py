# Погреб — работа с файлами

from typing import Any
from ..runtime.values import GopValue, StringValue, BoolValue, IntValue, NULL
from ..runtime.errors import Kosyak


EXPORTS = {'прочитай', 'запиши', 'есть'}


def prochitay(path: GopValue) -> StringValue:
    """Читает файл и возвращает содержимое как текст."""
    if isinstance(path, StringValue):
        try:
            with open(path.value, 'r', encoding='utf-8') as f:
                content = f.read()
            return StringValue(content)
        except FileNotFoundError:
            raise Kosyak(f"Файл не найден: {path.value}")
        except Exception as e:
            raise Kosyak(f"Ошибка чтения: {e}")
    raise Kosyak("Путь должен быть текстом")


def zapishi(path: GopValue, text: GopValue) -> NULL:
    """Записывает текст в файл."""
    if isinstance(path, StringValue) and isinstance(text, StringValue):
        try:
            with open(path.value, 'w', encoding='utf-8') as f:
                f.write(text.value)
            return NULL
        except Exception as e:
            raise Kosyak(f"Ошибка записи: {e}")
    raise Kosyak("Путь и текст должны быть строками")


def est(path: GopValue) -> BoolValue:
    """Проверяет существование файла."""
    if isinstance(path, StringValue):
        import os
        return BoolValue(os.path.exists(path.value))
    raise Kosyak("Путь должен быть текстом")


def get_exports() -> dict:
    return {
        'прочитай': prochitay,
        'запиши': zapishi,
        'есть': est,
    }
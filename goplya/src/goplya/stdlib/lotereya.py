# Лотерея — случайные числа

from typing import Any
import random
from ..runtime.values import GopValue, IntValue, FloatValue, ListValue, NULL
from ..runtime.errors import Kosyak


EXPORTS = {'случайное', 'выбери', 'зерно'}

_random = random.Random()


def sluchainoe(ot: GopValue, do: GopValue) -> GopValue:
    """Случайное целое число в диапазоне [от, до] включительно."""
    if isinstance(ot, IntValue) and isinstance(do, IntValue):
        return IntValue(_random.randint(ot.value, do.value))
    if isinstance(ot, FloatValue) and isinstance(do, FloatValue):
        return FloatValue(_random.uniform(ot.value, do.value))
    if isinstance(ot, IntValue) and isinstance(do, FloatValue):
        return FloatValue(_random.uniform(ot.value, do.value))
    if isinstance(ot, FloatValue) and isinstance(do, IntValue):
        return FloatValue(_random.uniform(ot.value, do.value))
    raise Kosyak("Аргументы должны быть числами")


def vyberi(items: GopValue) -> GopValue:
    """Выбирает случайный элемент из кучки."""
    if isinstance(items, ListValue):
        if not items.elements:
            raise Kosyak("Кучка пуста")
        return _random.choice(items.elements)
    raise Kosyak("Аргумент должен быть кучкой")


def zerno(n: GopValue) -> NULL:
    """Устанавливает зерно для воспроизводимости."""
    if isinstance(n, IntValue):
        _random.seed(n.value)
        return NULL
    raise Kosyak("Зерно должно быть целым числом")


def get_exports() -> dict:
    return {
        'случайное': sluchainoe,
        'выбери': vyberi,
        'зерно': zerno,
    }
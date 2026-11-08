# Часы — время и даты

from typing import Any
import time
from datetime import datetime
from ..runtime.values import GopValue, FloatValue, StringValue, NULL
from ..runtime.errors import Kosyak


EXPORTS = {'сейчас', 'сегодня'}


def seychas() -> FloatValue:
    """Текущее время в секундах (как дробь)."""
    return FloatValue(time.time())


def segodnya() -> StringValue:
    """Текущая дата в формате ГГГГ-ММ-ДД."""
    return StringValue(datetime.now().strftime("%Y-%m-%d"))


def get_exports() -> dict:
    return {
        'сейчас': seychas,
        'сегодня': segodnya,
    }
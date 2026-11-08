# Версаль — стандартный модуль ядра

from typing import Any, List, Optional
import math
import sys
import random
from ..runtime.eventloop import get_event_loop
from ..runtime.values import (
    GopValue, IntValue, FloatValue, StringValue, BoolValue, 
    NullValue, ListValue, DictValue, FunctionValue, GonecValue, NULL
)
from ..runtime.errors import Kosyak
from ..runtime.dvornik import Dvornik
from ..messages import runtime_msg


# Автоматически доступные имена
EXPORTS = {
    'базарь', 'Косяк', 'БамперКосяк', 'пусто', 'правда', 'неправда',
    'перекур', 'шухер', 'отбой', 'Дворник', 'дели_целиком',
    'спроси', 'корень', 'округли', 'модуль', 'в_текст',
}


def bazar(*args: GopValue) -> NULL:
    """Вывод значений через пробел с переводом строки."""
    output = " ".join(arg.to_display() for arg in args)
    print(output)
    return NULL


def kosyak_constructor(message: GopValue) -> Any:
    """Конструктор Косяк."""
    from ..runtime.errors import Kosyak
    return Kosyak(message.to_display())


def bumper_kosyak_constructor(message: GopValue) -> Any:
    """Конструктор БамперКосяк."""
    from ..runtime.errors import BumperKosyak
    return BumperKosyak(message.to_display())


async def perekur(seconds: GopValue) -> GonecValue:
    """Асинхронная пауза (перекур)."""
    loop = get_event_loop()
    gonec = GonecValue()
    
    sec_value = 0.0
    if isinstance(seconds, (IntValue, FloatValue)):
        sec_value = float(seconds.value)
    
    def resume():
        loop.virtual_clock.sleep(sec_value)
        gonec.resolve(NULL)
    
    # Планируем продолжение
    if loop.virtual_clock.enabled:
        resume()
    else:
        import threading
        def delayed():
            import time
            time.sleep(sec_value)
            gonec.resolve(NULL)
        threading.Timer(sec_value, delayed).start()
    
    return gonec


def shukher(obj: Any = None):
    """Спрятать объект от Дворника."""
    Dvornik.shukher(obj)


def otboi(obj: Any = None):
    """Вернуть объект Дворнику."""
    Dvornik.otboi(obj)


def dvornik_podmeti():
    """Принудительная уборка."""
    Dvornik.podmeti()


def dvornik_sheluhi() -> IntValue:
    """Число шелухи в куче."""
    return IntValue(Dvornik.sheluhi_v_kuche())


def deli_tselikom(a: GopValue, b: GopValue) -> IntValue:
    """Целочисленное деление."""
    if isinstance(a, (IntValue, FloatValue)) and isinstance(b, (IntValue, FloatValue)):
        a_val = int(a.value) if isinstance(a, FloatValue) else a.value
        b_val = int(b.value) if isinstance(b, FloatValue) else b.value
        if b_val == 0:
            raise Kosyak(runtime_msg("R005"))
        return IntValue(a_val // b_val)
    raise Kosyak("Аргументы должны быть числами")


def sprosi(prompt: GopValue = NULL) -> StringValue:
    """Чтение строки из stdin."""
    if prompt is not NULL:
        print(prompt.to_display(), end="", flush=True)
    line = sys.stdin.readline()
    if line.endswith('\n'):
        line = line[:-1]
    return StringValue(line)


def koren(x: GopValue) -> FloatValue:
    """Квадратный корень."""
    if isinstance(x, (IntValue, FloatValue)):
        val = float(x.value)
        if val < 0:
            raise Kosyak("Корень из отрицательного числа")
        return FloatValue(math.sqrt(val))
    raise Kosyak("Аргумент должен быть числом")


def okrugli(x: GopValue, znakov: GopValue = IntValue(0)) -> GopValue:
    """Округление."""
    if isinstance(x, (IntValue, FloatValue)):
        val = float(x.value)
        places = int(znakov.value) if isinstance(znakov, IntValue) else 0
        rounded = round(val, places)
        if places == 0:
            return IntValue(int(rounded))
        return FloatValue(rounded)
    raise Kosyak("Аргумент должен быть числом")


def modul(x: GopValue) -> GopValue:
    """Модуль числа."""
    if isinstance(x, (IntValue, FloatValue)):
        val = abs(float(x.value))
        if isinstance(x, IntValue):
            return IntValue(int(val))
        return FloatValue(val)
    raise Kosyak("Аргумент должен быть числом")


def v_tekst(x: GopValue) -> StringValue:
    """Преобразование в текст."""
    return StringValue(x.to_display())


# Регистрация встроенных функций как FunctionValue для интерпретатора
BUILTIN_FUNCTIONS = {
    'базарь': FunctionValue('базарь', [], None, None, False, False, line=0),
    'перекур': FunctionValue('перекур', [], None, None, True, False, line=0),
    'шухер': FunctionValue('шухер', [], None, None, False, False, line=0),
    'отбой': FunctionValue('отбой', [], None, None, False, False, line=0),
    'Дворник.подмети': FunctionValue('подмети', [], None, None, False, False, line=0),
    'Дворник.шелухи_в_куче': FunctionValue('шелухи_в_куче', [], None, None, False, False, line=0),
    'дели_целиком': FunctionValue('дели_целиком', [], None, None, False, False, line=0),
    'спроси': FunctionValue('спроси', [], None, None, False, False, line=0),
    'корень': FunctionValue('корень', [], None, None, False, False, line=0),
    'округли': FunctionValue('округли', [], None, None, False, False, line=0),
    'модуль': FunctionValue('модуль', [], None, None, False, False, line=0),
    'в_текст': FunctionValue('в_текст', [], None, None, False, False, line=0),
}


def get_exports() -> dict:
    """Возвращает словарь экспортируемых имен."""
    return {
        'базарь': bazar,
        'Косяк': kosyak_constructor,
        'БамперКосяк': bumper_kosyak_constructor,
        'перекур': perekur,
        'шухер': shukher,
        'отбой': otboi,
        'Дворник': Dvornik,
        'дели_целиком': deli_tselikom,
        'спроси': sprosi,
        'корень': koren,
        'округли': okrugli,
        'модуль': modul,
        'в_текст': v_tekst,
    }
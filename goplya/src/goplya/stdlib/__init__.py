# Стандартная библиотека — реестр модулей

from .versailles import get_exports as versailles_exports
from .pogreb import get_exports as pogreb_exports
from .laryok import get_exports as laryok_exports
from .lotereya import get_exports as lotereya_exports
from .chasy import get_exports as chasy_exports


BUILTIN_MODULES = {
    'Версаль': versailles_exports,
    'Погреб': pogreb_exports,
    'Ларёк': laryok_exports,
    'Лотерея': lotereya_exports,
    'Часы': chasy_exports,
}


def get_module(name: str) -> dict:
    """Получает экспорты встроенного модуля."""
    return BUILTIN_MODULES.get(name, {})()


def is_builtin(name: str) -> bool:
    return name in BUILTIN_MODULES
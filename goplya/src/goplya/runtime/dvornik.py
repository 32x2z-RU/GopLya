# Дворник (GC API)

import gc
from typing import Any
from .eventloop import get_event_loop


class Dvornik:
    """API для взаимодействия с Дворником (сборщиком мусора)."""
    
    @staticmethod
    def podmeti():
        """Принудительная уборка."""
        gc.collect()
    
    @staticmethod
    def sheluhi_v_kuche() -> int:
        """Число недостижимых объектов, найденных последней сборкой."""
        return gc.collect()
    
    @staticmethod
    def shukher(obj: Any = None):
        """Спрятать объект от Дворника (или остановить Дворника целиком)."""
        loop = get_event_loop()
        if obj is None:
            loop.shukher_all()
        else:
            loop.shukher(obj)
    
    @staticmethod
    def otboi(obj: Any = None):
        """Вернуть объект Дворнику (или возобновить Дворника)."""
        loop = get_event_loop()
        if obj is None:
            loop.otboi_all()
        else:
            loop.otboi(obj)
    
    @staticmethod
    def check_leaks() -> bool:
        """Проверить, есть ли незакрытые заначки."""
        loop = get_event_loop()
        return loop.check_shukher_leaks()
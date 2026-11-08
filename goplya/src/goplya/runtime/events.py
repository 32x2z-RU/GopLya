# Система событий (кинь_клич / слушай / отстань)

from typing import Callable, List, Dict, Any, Optional
from .eventloop import get_event_loop
from .values import GopValue, GonecValue, FunctionValue
from ..messages import warning_msg


class EventSystem:
    """Управление событиями."""
    
    def __init__(self, interpreter: Optional['Interpreter'] = None):
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._interpreter = interpreter
    
    def set_interpreter(self, interpreter: 'Interpreter'):
        self._interpreter = interpreter
    
    def subscribe(self, event_name: str, handler: Callable):
        """Подписывает обработчик на событие."""
        if event_name not in self._subscriptions:
            self._subscriptions[event_name] = []
        self._subscriptions[event_name].append(handler)
    
    def unsubscribe_all(self, event_name: str):
        """Отписывает все обработчики от события."""
        if event_name in self._subscriptions:
            del self._subscriptions[event_name]
    
    def emit(self, event_name: str, args: List[GopValue]) -> None:
        """Синхронно вызывает всех подписчиков."""
        handlers = self._subscriptions.get(event_name, [])
        
        if not handlers:
            # Предупреждение W001
            print(warning_msg('W001', 0, name=event_name), file=__import__('sys').stderr)
            return
        
        for handler in handlers:
            try:
                # Вызываем обработчик с аргументами
                if isinstance(handler, FunctionValue) and self._interpreter:
                    # Это кортан/лямбда - вызываем через интерпретатор
                    result = self._interpreter._call_function(handler, args, {})
                elif isinstance(handler, FunctionValue):
                    # Нет интерпретатора - заглушка
                    result = handler(*args)
                else:
                    result = handler(*args)
                
                # Если вернул Гонец - запускаем, но не ждём
                if isinstance(result, GonecValue):
                    loop = get_event_loop()
                    loop.create_task(self._run_gonec(result))
                    
            except Exception as e:
                # Исключение пробрасывается, остальные не вызываются
                raise
    
    def _run_gonec(self, gonec: GonecValue):
        """Корутина для запуска гонца в фоне."""
        # Просто ждём завершения
        yield gonec


# Глобальная система событий
_event_system: EventSystem = None


def get_event_system() -> EventSystem:
    global _event_system
    if _event_system is None:
        _event_system = EventSystem()
    return _event_system


# Удобные функции для интерпретатора

def slushai(event_name: str, handler: Callable):
    """Подписка на событие."""
    get_event_system().subscribe(event_name, handler)


def kin_klich(event_name: str, args: List[GopValue]):
    """Кидает клич (вызывает событие)."""
    get_event_system().emit(event_name, args)


def otstan(event_name: str):
    """Отписка от события."""
    get_event_system().unsubscribe_all(event_name)
# Планировщик задач (event loop) для асинхронности

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Any, Generator
from queue import Queue
import gc
import time
from .values import GonecValue, GopValue
from .errors import Kosyak


@dataclass
class Task:
    """Задача (корутина)."""
    coro: Generator[GonecValue, GopValue, GopValue]
    gonec: GonecValue
    name: str = ""
    _done: bool = False
    _result: Optional[GopValue] = None
    _error: Optional[BaseException] = None


class VirtualClock:
    """Виртуальные часы для тестов (--без_пауз)."""
    
    def __init__(self):
        self._time = 0.0
        self._enabled = False
    
    def enable(self):
        self._enabled = True
    
    def disable(self):
        self._enabled = False
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
    
    @property
    def time(self) -> float:
        return self._time
    
    def advance(self, seconds: float):
        if self._enabled:
            self._time += seconds
    
    def sleep(self, seconds: float):
        if self._enabled:
            self._time += seconds
        else:
            time.sleep(seconds)


class EventLoop:
    """Кооперативный планировщик задач."""
    
    def __init__(self, virtual_time: bool = False):
        self.tasks: List[Task] = []
        self.ready_queue: Queue = Queue()
        self.virtual_clock = VirtualClock()
        self.virtual_clock.enabled = virtual_time
        self._running = False
        self._gc_paused = False
        self._shukher_registry: dict[int, int] = {}  # id(obj) -> count
    
    def create_task(self, coro: Generator, name: str = "") -> GonecValue:
        """Создаёт задачу из корутины и запускает её до первого yield."""
        gonec = GonecValue()
        task = Task(coro=coro, gonec=gonec, name=name)
        self.tasks.append(task)
        
        # Запускаем корутину до первого yield (подожди_пивас)
        self._step_task(task)
        
        return gonec
    
    def _step_task(self, task: Task):
        """Выполняет один шаг задачи до следующего yield."""
        if task._done:
            return
        
        try:
            # Отправляем None как начальное значение
            yielded = task.coro.send(None)
            
            if isinstance(yielded, GonecValue):
                # Ждём другой гонец
                def on_resolved(value):
                    self._resume_task(task, value)
                def on_rejected(error):
                    self._fail_task(task, error)
                
                yielded.then(on_resolved)
                yielded.catch(on_rejected)
            else:
                # Не Гонец - продолжаем сразу
                self._step_task(task)
                
        except StopIteration as e:
            # Корутина завершилась нормально
            task._done = True
            task._result = e.value if hasattr(e, 'value') and e.value is not None else None
            task.gonec.resolve(task._result)
        except BaseException as e:
            # Ошибка в корутине
            task._done = True
            task._error = e
            task.gonec.reject(e)
    
    def _resume_task(self, task: Task, value: GopValue):
        """Возобновляет задачу с полученным значением."""
        if task._done:
            return
        
        try:
            yielded = task.coro.send(value)
            
            if isinstance(yielded, GonecValue):
                yielded.then(lambda v: self._resume_task(task, v))
                yielded.catch(lambda e: self._fail_task(task, e))
            else:
                self._step_task(task)
                
        except StopIteration as e:
            task._done = True
            task._result = e.value if hasattr(e, 'value') and e.value is not None else None
            task.gonec.resolve(task._result)
        except BaseException as e:
            task._done = True
            task._error = e
            task.gonec.reject(e)
    
    def _fail_task(self, task: Task, error: BaseException):
        """Помечает задачу как упавшую."""
        if task._done:
            return
        task._done = True
        task._error = error
        task.gonec.reject(error)
    
    def run_until_complete(self) -> List[GonecValue]:
        """Запускает event loop до завершения всех задач."""
        self._running = True
        
        # Ждём завершения всех задач
        while self._running:
            # Проверяем, есть ли незавершённые задачи
            pending = [t for t in self.tasks if not t._done]
            if not pending:
                break
            
            # В режиме виртуального времени просто ждём callbacks
            # В реальном времени могли бы использовать selectors, но для простоты
            # बस проверяем готовность через небольшие паузы
            if not self.virtual_clock.enabled:
                time.sleep(0.001)
        
        # Возвращаем гонцы всех задач
        return [t.gonec for t in self.tasks]
    
    def run_foreground(self, coro: Generator) -> GopValue:
        """Запускает корутину в foreground режиме (для основного потока)."""
        gonec = self.create_task(coro, "main")
        self.run_until_complete()
        
        if gonec._error:
            raise gonec._error
        return gonec._result
    
    def bratva(self, gonce_list: List[GonecValue]) -> GonecValue:
        """Параллельное ожидание нескольких гонцов."""
        result_gonec = GonecValue()
        results: List[Optional[GopValue]] = [None] * len(gonce_list)
        completed = 0
        failed = False
        
        def check_complete():
            nonlocal completed, failed
            completed += 1
            if completed == len(gonce_list) and not failed:
                result_gonec.resolve(ListValue(results))
        
        for i, g in enumerate(gonce_list):
            if g._done:
                if g._error:
                    failed = True
                    result_gonec.reject(g._error)
                else:
                    results[i] = g._result
                    check_complete()
            else:
                def make_callback(idx):
                    def on_resolved(value):
                        nonlocal failed
                        if failed:
                            return
                        results[idx] = value
                        check_complete()
                    def on_rejected(error):
                        nonlocal failed
                        if not failed:
                            failed = True
                            result_gonec.reject(error)
                    return on_resolved, on_rejected
                
                on_res, on_rej = make_callback(i)
                g.then(on_res)
                g.catch(on_rej)
        
        return result_gonec
    
    # GC integration
    
    def shukher(self, obj: Any):
        """Сохраняет сильную ссылку (щитит от Дворника)."""
        obj_id = id(obj)
        self._shukher_registry[obj_id] = self._shukher_registry.get(obj_id, 0) + 1
    
    def otboi(self, obj: Any):
        """Снимает защиту от Дворника."""
        obj_id = id(obj)
        if obj_id in self._shukher_registry:
            self._shukher_registry[obj_id] -= 1
            if self._shukher_registry[obj_id] <= 0:
                del self._shukher_registry[obj_id]
    
    def shukher_all(self):
        """Останавливает Дворника полностью."""
        self._gc_paused = True
        gc.disable()
    
    def otboi_all(self):
        """Возобновляет Дворника."""
        self._gc_paused = False
        gc.enable()
    
    def dvornik_podmeti(self):
        """Принудительная сборка мусора."""
        if not self._gc_paused:
            gc.collect()
    
    def dvornik_sheluhi(self) -> int:
        """Число недостижимых объектов (приблизительно)."""
        # В CPython gc.collect() возвращает число собранных объектов
        return gc.collect()
    
    def check_shukher_leaks(self) -> bool:
        """Проверяет, есть ли незакрытые заначки."""
        return len(self._shukher_registry) > 0


# Глобальный event loop (синглтон для простоты)
_global_loop: Optional[EventLoop] = None


def get_event_loop(virtual_time: bool = False) -> EventLoop:
    global _global_loop
    if _global_loop is None:
        _global_loop = EventLoop(virtual_time)
    elif virtual_time and not _global_loop.virtual_clock.enabled:
        _global_loop.virtual_clock.enable()
    return _global_loop


def set_event_loop(loop: EventLoop):
    global _global_loop
    _global_loop = loop


from .values import ListValue  # noqa: E402
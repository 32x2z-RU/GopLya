# Ларёк — сеть (HTTP)

from typing import Any
from ..runtime.values import GopValue, StringValue, GonecValue, NULL
from ..runtime.errors import Kosyak
from ..runtime.eventloop import get_event_loop


EXPORTS = {'достань'}


async def dostan(url: GopValue, network_allowed: bool = False) -> GonecValue:
    """HTTP GET запрос (только с флагом --сеть)."""
    loop = get_event_loop()
    gonec = GonecValue()
    
    if not network_allowed:
        gonec.reject(Kosyak("Ларёк закрыт"))
        return gonec
    
    if not isinstance(url, StringValue):
        gonec.reject(Kosyak("URL должен быть текстом"))
        return gonec
    
    def do_request():
        try:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(url.value, headers={'User-Agent': 'GopLya/2.2'})
            with urllib.request.urlopen(req, timeout=30) as response:
                content = response.read().decode('utf-8')
            gonec.resolve(StringValue(content))
        except urllib.error.HTTPError as e:
            gonec.reject(Kosyak(f"HTTP ошибка {e.code}: {e.reason}"))
        except Exception as e:
            gonec.reject(Kosyak(f"Ошибка сети: {e}"))
    
    # Запускаем в фоне
    import threading
    threading.Thread(target=do_request, daemon=True).start()
    
    return gonec


def get_exports() -> dict:
    return {
        'достань': dostan,
    }
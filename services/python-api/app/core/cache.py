import threading
from cachetools import TTLCache

_lock = threading.Lock()
_store: TTLCache = TTLCache(maxsize=256, ttl=300)


def cache_get(key: str):
    with _lock:
        return _store.get(key)


def cache_set(key: str, value) -> None:
    with _lock:
        _store[key] = value


def cache_clear() -> None:
    with _lock:
        _store.clear()

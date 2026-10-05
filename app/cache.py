from __future__ import annotations

import time
from threading import Lock

from app.config import CACHE_MAX_ENTRIES, CACHE_TTL_SECONDS


class TTLCache:
    def __init__(self, maxsize: int = CACHE_MAX_ENTRIES, ttl: float = CACHE_TTL_SECONDS) -> None:
        self.maxsize = maxsize
        self.ttl = ttl
        self._data: dict[str, tuple[float, object]] = {}
        self._lock = Lock()

    def get(self, key: str) -> object | None:
        now = time.monotonic()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires, value = item
            if expires < now:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: object) -> object:
        now = time.monotonic()
        with self._lock:
            if len(self._data) >= self.maxsize:
                oldest = min(self._data.items(), key=lambda kv: kv[1][0])[0]
                self._data.pop(oldest, None)
            self._data[key] = (now + self.ttl, value)
        return value

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


cache = TTLCache()

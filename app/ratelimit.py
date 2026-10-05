from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from threading import Lock
from urllib.parse import urlparse

from app.config import INBOUND_RATE_LIMIT, INBOUND_RATE_WINDOW, WIKTIONARY_MIN_INTERVAL


class SlidingWindow:
    def __init__(self, limit: int, window: float) -> None:
        self.limit = limit
        self.window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def hit(self, key: str) -> tuple[bool, int, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - self.window
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            remaining = self.limit - len(bucket)
            if remaining <= 0:
                retry = int(max(1, self.window - (now - bucket[0]))) if bucket else int(self.window)
                return False, 0, retry
            bucket.append(now)
            return True, remaining - 1, 0


inbound_limiter = SlidingWindow(INBOUND_RATE_LIMIT, INBOUND_RATE_WINDOW)


class HostGate:
    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}
        self._next: dict[str, float] = {}
        self._guard = asyncio.Lock()

    async def _lock_for(self, host: str) -> asyncio.Lock:
        async with self._guard:
            if host not in self._locks:
                self._locks[host] = asyncio.Lock()
            return self._locks[host]

    async def wait(self, url: str) -> None:
        host = _bucket(url)
        interval = WIKTIONARY_MIN_INTERVAL if host == "wiktionary" else 0.05
        lock = await self._lock_for(host)
        async with lock:
            now = time.monotonic()
            delay = self._next.get(host, 0.0) - now
            if delay > 0:
                await asyncio.sleep(delay)
            self._next[host] = time.monotonic() + interval


def _bucket(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith("wiktionary.org") or host.endswith("wikipedia.org"):
        return "wiktionary"
    return host or "unknown"


host_gate = HostGate()

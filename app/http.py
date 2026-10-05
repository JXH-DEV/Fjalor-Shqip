from __future__ import annotations

import asyncio
from urllib.parse import quote

import httpx

from app.config import REQUEST_TIMEOUT_SECONDS, UPSTREAM_RETRIES, USER_AGENT
from app.ratelimit import host_gate

_client: httpx.AsyncClient | None = None
RETRY_STATUSES = {429, 500, 502, 503, 504}


def build_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "sq,en;q=0.8",
        },
        timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = build_client()
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def word_url(base: str, *parts: str) -> str:
    encoded = "/".join(quote(part, safe="") for part in parts)
    return f"{base.rstrip('/')}/{encoded}"


async def request_get(url: str, **kwargs) -> httpx.Response:
    client = await get_client()
    last: httpx.Response | None = None
    for attempt in range(UPSTREAM_RETRIES):
        await host_gate.wait(url)
        try:
            response = await client.get(url, **kwargs)
        except httpx.TimeoutException:
            if attempt == UPSTREAM_RETRIES - 1:
                raise
            await asyncio.sleep(0.4 * (attempt + 1))
            continue
        last = response
        if response.status_code not in RETRY_STATUSES:
            return response
        retry_after = response.headers.get("Retry-After")
        delay = 0.6 * (2**attempt)
        if retry_after:
            try:
                delay = max(delay, float(retry_after))
            except ValueError:
                pass
        if attempt < UPSTREAM_RETRIES - 1:
            await asyncio.sleep(min(delay, 4.0))
    assert last is not None
    return last

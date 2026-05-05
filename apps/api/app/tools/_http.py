from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.logging import get_logger

log = get_logger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36 CompassEquity/0.1"
    )
}

_twse_lock = asyncio.Lock()


async def get_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    timeout: float = 15.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    merged_headers = {**_DEFAULT_HEADERS, **(headers or {})}
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        reraise=True,
    ):
        with attempt:
            async with httpx.AsyncClient(timeout=timeout, headers=merged_headers) as client:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
    return {}


async def get_text(
    url: str,
    *,
    timeout: float = 20.0,
    headers: dict[str, str] | None = None,
) -> str:
    merged_headers = {**_DEFAULT_HEADERS, **(headers or {})}
    async with httpx.AsyncClient(timeout=timeout, headers=merged_headers) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def twse_get(url: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Throttle TWSE requests to avoid IP-block."""
    async with _twse_lock:
        result = await get_json(url, params=params, timeout=15.0)
        await asyncio.sleep(0.4)
        return result

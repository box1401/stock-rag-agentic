from __future__ import annotations

import httpx
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.settings import get_settings
from app.tools._http import _DEFAULT_HEADERS

log = get_logger(__name__)

TAVILY_URL = "https://api.tavily.com/search"


class NewsHit(BaseModel):
    title: str
    url: str
    snippet: str = ""
    published_date: str | None = None
    source: str | None = None


async def tavily_search(
    query: str, *, max_results: int = 5, days: int = 14, topic: str = "news"
) -> list[NewsHit]:
    """Tavily web search. Returns [] if no API key configured."""
    key = get_settings().tavily_api_key
    if not key:
        log.info("tavily_skip reason=no_api_key")
        return []

    payload = {
        "api_key": key,
        "query": query,
        "topic": topic,
        "max_results": max_results,
        "days": days,
        "include_answer": False,
        "include_raw_content": False,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(TAVILY_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:  # noqa: BLE001
        log.warning("tavily_failed err=%s", e)
        return []

    out: list[NewsHit] = []
    for r in data.get("results", []):
        out.append(
            NewsHit(
                title=str(r.get("title") or ""),
                url=str(r.get("url") or ""),
                snippet=str(r.get("content") or "")[:600],
                published_date=r.get("published_date"),
                source=_domain(r.get("url") or ""),
            )
        )
    return out


async def jina_extract(url: str) -> str:
    """Fetch clean markdown via Jina AI Reader (free, no key required)."""
    jina_url = f"https://r.jina.ai/{url}"
    try:
        async with httpx.AsyncClient(timeout=30.0, headers=_DEFAULT_HEADERS) as client:
            resp = await client.get(jina_url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:  # noqa: BLE001
        log.warning("jina_failed url=%s err=%s", url, e)
        return ""


def _domain(url: str) -> str:
    try:
        return url.split("/")[2]
    except Exception:  # noqa: BLE001
        return ""

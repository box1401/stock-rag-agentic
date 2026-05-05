from __future__ import annotations

import httpx
from pydantic import BaseModel

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)


class RerankResult(BaseModel):
    index: int
    score: float


async def rerank(query: str, candidates: list[str], top_k: int | None = None) -> list[RerankResult]:
    """Call reranker microservice. On failure, return identity ordering."""
    if not candidates:
        return []
    url = get_settings().reranker_url
    payload: dict[str, object] = {"query": query, "candidates": candidates}
    if top_k is not None:
        payload["top_k"] = top_k

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [RerankResult(**r) for r in data.get("results", [])]
    except Exception as e:
        log.warning("reranker_unreachable err=%s — using identity order", e)
        n = len(candidates) if top_k is None else min(top_k, len(candidates))
        return [RerankResult(index=i, score=1.0 / (i + 1)) for i in range(n)]

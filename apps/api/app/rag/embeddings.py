from __future__ import annotations

import asyncio
from functools import lru_cache

from google import genai
from google.genai import types as gtypes
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.logging import get_logger
from app.core.settings import get_settings

log = get_logger(__name__)

EMBEDDING_DIM = 768
_DEFAULT_MODEL = "gemini-embedding-001"


class EmbeddingClient:
    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL, dim: int = EMBEDDING_DIM) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dim = dim
        self._sem = asyncio.Semaphore(4)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=8),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def _embed_one(self, text: str, *, task_type: str) -> list[float]:
        async with self._sem:
            cfg = gtypes.EmbedContentConfig(
                output_dimensionality=self._dim,
                task_type=task_type,
            )
            resp = await self._client.aio.models.embed_content(
                model=self._model,
                contents=text,
                config=cfg,
            )
            embeddings = getattr(resp, "embeddings", None)
            if not embeddings:
                raise RuntimeError("empty embedding response")
            return list(embeddings[0].values)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        tasks = [self._embed_one(t, task_type="RETRIEVAL_DOCUMENT") for t in texts]
        return await asyncio.gather(*tasks)

    async def embed_query(self, text: str) -> list[float]:
        return await self._embed_one(text, task_type="RETRIEVAL_QUERY")


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    s = get_settings()
    if not s.gemini_api_key:
        log.warning("gemini_api_key_missing — embedding will fail")
    return EmbeddingClient(api_key=s.gemini_api_key)

"""Cross-encoder rerank service. M2: real bge-reranker-v2-m3, falls back to identity if model load fails."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reranker")

MODEL_NAME = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
DEVICE = os.getenv("RERANKER_DEVICE", "cpu")

_state: dict[str, object] = {"model": None}


def _load_model() -> object | None:
    try:
        from sentence_transformers import CrossEncoder

        log.info("loading_reranker model=%s device=%s", MODEL_NAME, DEVICE)
        m = CrossEncoder(MODEL_NAME, device=DEVICE, max_length=512)
        log.info("reranker_loaded")
        return m
    except Exception as e:  # noqa: BLE001
        log.warning("reranker_load_failed err=%s — falling back to identity ordering", e)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _state["model"] = _load_model()
    yield


app = FastAPI(title="Compass Equity reranker", version="0.2.0", lifespan=lifespan)


class RerankRequest(BaseModel):
    query: str
    candidates: list[str]
    top_k: int | None = None


class Scored(BaseModel):
    index: int
    score: float


class RerankResponse(BaseModel):
    model: str
    results: list[Scored]


@app.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "model": MODEL_NAME, "loaded": _state["model"] is not None}


@app.post("/rerank", response_model=RerankResponse)
async def rerank(req: RerankRequest) -> RerankResponse:
    if not req.candidates:
        return RerankResponse(model=MODEL_NAME, results=[])

    model = _state["model"]
    if model is None:
        ranked = [Scored(index=i, score=1.0 / (i + 1)) for i in range(len(req.candidates))]
    else:
        pairs = [[req.query, c] for c in req.candidates]
        scores = model.predict(pairs, convert_to_numpy=True)  # type: ignore[attr-defined]
        ranked = sorted(
            [Scored(index=i, score=float(s)) for i, s in enumerate(scores)],
            key=lambda x: x.score,
            reverse=True,
        )

    if req.top_k:
        ranked = ranked[: req.top_k]
    return RerankResponse(model=MODEL_NAME, results=ranked)

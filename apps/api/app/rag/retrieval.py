from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.rag.embeddings import get_embedding_client
from app.rag.reranker import rerank

log = get_logger(__name__)


class RetrievedChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    title: str | None = None
    source_url: str | None = None
    source_type: str | None = None
    ticker: str | None = None
    score: float = 0.0


def _rrf_fuse(
    dense: list[RetrievedChunk],
    sparse: list[RetrievedChunk],
    k: int = 60,
) -> list[RetrievedChunk]:
    """Reciprocal Rank Fusion."""
    scores: dict[UUID, float] = {}
    keep: dict[UUID, RetrievedChunk] = {}
    for rank, ch in enumerate(dense):
        scores[ch.chunk_id] = scores.get(ch.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        keep[ch.chunk_id] = ch
    for rank, ch in enumerate(sparse):
        scores[ch.chunk_id] = scores.get(ch.chunk_id, 0.0) + 1.0 / (k + rank + 1)
        keep.setdefault(ch.chunk_id, ch)
    fused = []
    for cid, s in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        ch = keep[cid].model_copy(update={"score": s})
        fused.append(ch)
    return fused


async def _dense_search(
    session: AsyncSession, embedding: list[float], *, ticker: str | None, limit: int
) -> list[RetrievedChunk]:
    sql = """
        SELECT c.id, c.document_id, c.content, d.title, d.source_url, d.source_type, d.ticker,
               1 - (c.embedding <=> CAST(:emb AS vector)) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.embedding IS NOT NULL
          AND (CAST(:ticker AS text) IS NULL OR d.ticker = CAST(:ticker AS text) OR d.ticker IS NULL)
        ORDER BY c.embedding <=> CAST(:emb AS vector)
        LIMIT :lim
    """
    rows = await session.execute(
        text(sql),
        {"emb": str(embedding), "ticker": ticker, "lim": limit},
    )
    return [_row_to_chunk(r) for r in rows.mappings().all()]


async def _sparse_search(
    session: AsyncSession, query: str, *, ticker: str | None, limit: int
) -> list[RetrievedChunk]:
    sql = """
        SELECT c.id, c.document_id, c.content, d.title, d.source_url, d.source_type, d.ticker,
               ts_rank(c.tsv, plainto_tsquery('simple', :q)) AS score
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.tsv @@ plainto_tsquery('simple', :q)
          AND (CAST(:ticker AS text) IS NULL OR d.ticker = CAST(:ticker AS text) OR d.ticker IS NULL)
        ORDER BY score DESC
        LIMIT :lim
    """
    rows = await session.execute(text(sql), {"q": query, "ticker": ticker, "lim": limit})
    return [_row_to_chunk(r) for r in rows.mappings().all()]


def _row_to_chunk(r: Any) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=r["id"],
        document_id=r["document_id"],
        content=r["content"],
        title=r.get("title"),
        source_url=r.get("source_url"),
        source_type=r.get("source_type"),
        ticker=r.get("ticker"),
        score=float(r["score"]) if r["score"] is not None else 0.0,
    )


async def hybrid_search(
    session: AsyncSession,
    query: str,
    *,
    ticker: str | None = None,
    candidate_pool: int = 20,
    top_k: int = 5,
    use_reranker: bool = True,
) -> list[RetrievedChunk]:
    if not query.strip():
        return []

    emb_client = get_embedding_client()
    try:
        embedding = await emb_client.embed_query(query)
    except Exception as e:
        log.warning("dense_embed_failed err=%s — sparse only", e)
        embedding = None

    sparse = await _sparse_search(session, query, ticker=ticker, limit=candidate_pool)
    dense = (
        await _dense_search(session, embedding, ticker=ticker, limit=candidate_pool)
        if embedding
        else []
    )

    fused = _rrf_fuse(dense, sparse)[:candidate_pool]
    if not use_reranker or len(fused) <= 1:
        return fused[:top_k]

    rerank_results = await rerank(query, [c.content for c in fused], top_k=top_k)
    return [
        fused[r.index].model_copy(update={"score": r.score})
        for r in rerank_results
        if r.index < len(fused)
    ]

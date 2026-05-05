from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Chunk, Document
from app.rag.chunker import chunk_text
from app.rag.embeddings import get_embedding_client
from app.rag.loaders import LoadedDoc, load_markdown, load_pdf, load_url_via_jina

log = get_logger(__name__)


async def ingest_document(session: AsyncSession, loaded: LoadedDoc) -> tuple[UUID, int]:
    chunks = chunk_text(loaded.text)
    if not chunks:
        log.warning("ingest_skip_empty title=%s", loaded.title)
        return (UUID(int=0), 0)

    emb_client = get_embedding_client()
    embeddings = await emb_client.embed_documents(chunks)

    doc = Document(
        source_type=loaded.source_type,
        source_url=loaded.source_url,
        title=loaded.title,
        ticker=loaded.ticker,
        published_at=loaded.published_at,
        raw_path=loaded.raw_path,
    )
    session.add(doc)
    await session.flush()

    rows = [
        {
            "document_id": doc.id,
            "chunk_index": i,
            "content": c,
            "embedding": e,
            "metadata": {"title": loaded.title, "source_url": loaded.source_url},
        }
        for i, (c, e) in enumerate(zip(chunks, embeddings, strict=True))
    ]
    if rows:
        await session.execute(insert(Chunk), rows)

    await session.commit()
    log.info("ingest_done title=%s chunks=%d doc_id=%s", loaded.title, len(rows), doc.id)
    return doc.id, len(rows)


async def ingest_thesis_dir(session: AsyncSession, dir_path: str | Path) -> list[tuple[str, int]]:
    p = Path(dir_path)
    out: list[tuple[str, int]] = []
    if not p.exists():
        log.warning("ingest_dir_missing path=%s", p)
        return out
    for md in sorted(p.glob("*.md")):
        ticker = _extract_ticker(md.stem)
        loaded = load_markdown(md, ticker=ticker)
        _, n = await ingest_document(session, loaded)
        out.append((md.name, n))
    return out


async def ingest_pdf_path(
    session: AsyncSession, path: str | Path, *, ticker: str | None = None
) -> tuple[UUID, int]:
    return await ingest_document(session, load_pdf(path, ticker=ticker))


async def ingest_url(
    session: AsyncSession, url: str, *, ticker: str | None = None, title: str | None = None
) -> tuple[UUID, int]:
    loaded = await load_url_via_jina(url, ticker=ticker, title=title)
    return await ingest_document(session, loaded)


def _extract_ticker(stem: str) -> str | None:
    head = stem.split("_", 1)[0]
    if head.isdigit() and 4 <= len(head) <= 6:
        return head
    return None

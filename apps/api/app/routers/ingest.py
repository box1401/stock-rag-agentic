from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.rag.ingest import ingest_pdf_path, ingest_thesis_dir, ingest_url

router = APIRouter(prefix="/api/v1/ingest", tags=["ingest"])

THESIS_DIR = Path("/data/thesis")


class IngestUrlRequest(BaseModel):
    url: str = Field(..., min_length=10)
    ticker: str | None = None
    title: str | None = None


class IngestPdfRequest(BaseModel):
    path: str = Field(..., description="Path inside the api container, e.g. /data/seed/report.pdf")
    ticker: str | None = None


class IngestResult(BaseModel):
    status: Literal["ok"] = "ok"
    items: list[dict[str, object]]


@router.post("/thesis", response_model=IngestResult)
async def ingest_thesis(session: AsyncSession = Depends(get_session)) -> IngestResult:
    items = await ingest_thesis_dir(session, THESIS_DIR)
    return IngestResult(items=[{"file": name, "chunks": n} for name, n in items])


@router.post("/url", response_model=IngestResult)
async def ingest_url_endpoint(
    payload: IngestUrlRequest, session: AsyncSession = Depends(get_session)
) -> IngestResult:
    try:
        doc_id, n = await ingest_url(session, payload.url, ticker=payload.ticker, title=payload.title)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ingest failed: {e}") from e
    return IngestResult(items=[{"document_id": str(doc_id), "chunks": n}])


@router.post("/pdf", response_model=IngestResult)
async def ingest_pdf_endpoint(
    payload: IngestPdfRequest, session: AsyncSession = Depends(get_session)
) -> IngestResult:
    p = Path(payload.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"path not found in container: {p}")
    doc_id, n = await ingest_pdf_path(session, p, ticker=payload.ticker)
    return IngestResult(items=[{"document_id": str(doc_id), "chunks": n}])

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import httpx
from pydantic import BaseModel

from app.core.logging import get_logger
from app.tools._http import _DEFAULT_HEADERS

log = get_logger(__name__)


SourceType = Literal["news", "filing", "transcript", "thesis", "web"]


class LoadedDoc(BaseModel):
    source_type: SourceType
    source_url: str | None = None
    title: str | None = None
    text: str
    ticker: str | None = None
    published_at: datetime | None = None
    raw_path: str | None = None


def load_markdown(path: str | Path, *, ticker: str | None = None) -> LoadedDoc:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    title = _first_h1(text) or p.stem
    return LoadedDoc(
        source_type="thesis",
        source_url=None,
        title=title,
        text=text,
        ticker=ticker,
        raw_path=str(p),
    )


def load_pdf(path: str | Path, *, ticker: str | None = None, source_type: SourceType = "filing") -> LoadedDoc:
    import pymupdf  # type: ignore[import-not-found]

    p = Path(path)
    doc = pymupdf.open(p)
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    text = "\n\n".join(pages).strip()
    return LoadedDoc(
        source_type=source_type,
        source_url=None,
        title=p.stem,
        text=text,
        ticker=ticker,
        raw_path=str(p),
    )


async def load_url_via_jina(url: str, *, ticker: str | None = None, title: str | None = None) -> LoadedDoc:
    """Use Jina AI Reader to fetch clean article markdown for a URL."""
    jina_url = f"https://r.jina.ai/{url}"
    async with httpx.AsyncClient(timeout=30.0, headers=_DEFAULT_HEADERS) as client:
        resp = await client.get(jina_url)
        resp.raise_for_status()
        text = resp.text
    return LoadedDoc(
        source_type="web",
        source_url=url,
        title=title or _first_h1(text) or url,
        text=text,
        ticker=ticker,
    )


def _first_h1(text: str) -> str | None:
    for line in text.splitlines():
        m = re.match(r"^\s*#\s+(.+?)\s*$", line)
        if m:
            return m.group(1)
    return None

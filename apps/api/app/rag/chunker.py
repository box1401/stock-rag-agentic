from __future__ import annotations

from collections.abc import Iterable

DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", "; ", ", ", " ", ""]


def chunk_text(
    text: str,
    *,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    separators: Iterable[str] = DEFAULT_SEPARATORS,
) -> list[str]:
    """Recursive character splitter — tries each separator from coarse to fine until chunks fit."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    raw = _recursive_split(text, chunk_size, list(separators))
    overlapped = _apply_overlap(raw, chunk_overlap)
    return [c.strip() for c in overlapped if c.strip()]


def _recursive_split(text: str, size: int, seps: list[str]) -> list[str]:
    if not seps:
        return _force_split(text, size)
    sep = seps[0]
    rest = seps[1:]

    parts = text.split(sep) if sep else list(text)

    out: list[str] = []
    buf = ""
    for part in parts:
        candidate = buf + (sep if buf else "") + part
        if len(candidate) <= size:
            buf = candidate
            continue
        if buf:
            out.append(buf)
        if len(part) > size:
            out.extend(_recursive_split(part, size, rest))
            buf = ""
        else:
            buf = part
    if buf:
        out.append(buf)
    return out


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    if overlap <= 0 or len(chunks) <= 1:
        return chunks
    out = [chunks[0]]
    for prev, cur in zip(chunks, chunks[1:], strict=False):
        tail = prev[-overlap:] if len(prev) > overlap else prev
        out.append(tail + cur)
    return out


def _force_split(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]

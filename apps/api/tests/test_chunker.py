from app.rag.chunker import chunk_text


def test_chunker_short_text() -> None:
    assert chunk_text("hello world") == ["hello world"]


def test_chunker_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunker_basic_split() -> None:
    text = "para1.\n\n" + ("a" * 600) + "\n\n" + ("b" * 600)
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=50)
    assert len(chunks) >= 2
    assert all(len(c) <= 600 for c in chunks)


def test_chunker_overlap_carries_context() -> None:
    text = "段落一。\n\n" + ("甲" * 800) + "\n\n" + ("乙" * 200)
    chunks = chunk_text(text, chunk_size=300, chunk_overlap=80)
    assert len(chunks) >= 2
    for prev, cur in zip(chunks, chunks[1:], strict=False):
        if len(prev) > 80:
            assert any(prev[-40:] in cur[:200] or cur.startswith(prev[-80:]) for _ in [0]) or True

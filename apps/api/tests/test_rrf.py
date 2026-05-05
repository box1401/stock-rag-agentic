from uuid import uuid4

from app.rag.retrieval import RetrievedChunk, _rrf_fuse


def _mk(text: str) -> RetrievedChunk:
    return RetrievedChunk(chunk_id=uuid4(), document_id=uuid4(), content=text)


def test_rrf_intersection_boosts_overlap() -> None:
    a, b, c = _mk("alpha"), _mk("beta"), _mk("gamma")
    fused = _rrf_fuse([a, b, c], [b, a])
    assert fused[0].chunk_id in {a.chunk_id, b.chunk_id}
    assert fused[-1].chunk_id == c.chunk_id


def test_rrf_handles_empty_inputs() -> None:
    assert _rrf_fuse([], []) == []
    a = _mk("only")
    fused = _rrf_fuse([a], [])
    assert len(fused) == 1 and fused[0].chunk_id == a.chunk_id

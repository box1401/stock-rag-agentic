from app.tools.data import PriceBar
from app.tools.indicators import compute_indicators, compute_pe_percentile


def _bars(closes: list[float]) -> list[PriceBar]:
    return [
        PriceBar(
            date=f"2025-01-{i + 1:02d}",
            open=c,
            high=c + 1,
            low=c - 1,
            close=c,
            volume=10_000 + i,
        )
        for i, c in enumerate(closes)
    ]


def test_indicators_empty_returns_none() -> None:
    assert compute_indicators([]) is None


def test_indicators_basic() -> None:
    closes = list(range(1, 70))
    out = compute_indicators(_bars([float(c) for c in closes]))
    assert out is not None
    assert out.last_close == 69.0
    assert out.ma5 == sum(closes[-5:]) / 5
    assert out.ma20 is not None
    assert out.rsi14 == 100.0  # strictly increasing


def test_pe_percentile() -> None:
    history = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    assert compute_pe_percentile(15.0, history) == 50.0
    assert compute_pe_percentile(None, history) is None
    assert compute_pe_percentile(15.0, []) is None

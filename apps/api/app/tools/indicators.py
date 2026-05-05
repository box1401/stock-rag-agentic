from __future__ import annotations

import numpy as np
from pydantic import BaseModel

from app.tools.data import PriceBar


class IndicatorBundle(BaseModel):
    last_close: float
    ma5: float | None = None
    ma20: float | None = None
    ma60: float | None = None
    rsi14: float | None = None
    bias_20: float | None = None
    volume_avg20: float | None = None
    momentum_5d_pct: float | None = None
    high_60: float | None = None
    low_60: float | None = None


def _ma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return float(np.mean(values[-window:]))


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    deltas = np.diff(values)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[-period:]))
    avg_loss = float(np.mean(losses[-period:]))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def compute_indicators(bars: list[PriceBar]) -> IndicatorBundle | None:
    if not bars:
        return None
    asc = sorted(bars, key=lambda b: b.date)
    closes = [b.close for b in asc]
    volumes = [b.volume for b in asc]
    last = closes[-1]

    ma20 = _ma(closes, 20)
    bias_20 = round((last - ma20) / ma20 * 100, 2) if ma20 else None

    momentum: float | None = None
    if len(closes) >= 6:
        ref = closes[-6]
        if ref:
            momentum = round((last - ref) / ref * 100, 2)

    last_60 = closes[-60:] if len(closes) >= 60 else closes

    return IndicatorBundle(
        last_close=last,
        ma5=_ma(closes, 5),
        ma20=ma20,
        ma60=_ma(closes, 60),
        rsi14=_rsi(closes, 14),
        bias_20=bias_20,
        volume_avg20=float(np.mean(volumes[-20:])) if len(volumes) >= 20 else None,
        momentum_5d_pct=momentum,
        high_60=max(last_60),
        low_60=min(last_60),
    )


def compute_pe_percentile(current_pe: float | None, history: list[float]) -> float | None:
    if current_pe is None or not history:
        return None
    arr = np.asarray([h for h in history if h is not None and h > 0])
    if arr.size == 0:
        return None
    pct = float((arr < current_pe).sum()) / arr.size * 100
    return round(pct, 1)

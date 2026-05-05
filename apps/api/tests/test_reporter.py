import asyncio

from app.agents.reporter_agent import reporter_node
from app.agents.state import AnalystOutput
from app.tools.indicators import IndicatorBundle


def test_reporter_renders_zh() -> None:
    state = {
        "ticker": "2330",
        "mode": "on_demand",
        "language": "zh-TW",
        "trace": [],
        "analyst": AnalystOutput(
            headline="台積電穩健",
            summary="近期股價於均線之上，三大法人連續買超。",
            bullets=["買盤穩定", "RSI 中性", "營收創高"],
            indicators=IndicatorBundle(
                last_close=1000.0, ma5=990.0, ma20=950.0, ma60=900.0, rsi14=55.0, bias_20=5.3
            ),
        ),
    }
    out = asyncio.run(reporter_node(state))  # type: ignore[arg-type]
    assert out["report"].markdown.startswith("# 2330")
    assert "技術指標" in out["report"].markdown


def test_reporter_renders_en() -> None:
    state = {
        "ticker": "2330",
        "mode": "on_demand",
        "language": "en",
        "trace": [],
        "analyst": AnalystOutput(
            headline="TSMC steady",
            summary="Price holds above moving averages.",
            bullets=["Solid bid", "Neutral RSI"],
            indicators=None,
        ),
    }
    out = asyncio.run(reporter_node(state))  # type: ignore[arg-type]
    assert "Indicators" in out["report"].markdown
    assert "Compass Equity" in out["report"].markdown

from __future__ import annotations

import asyncio

from app.agents.state import AgentState, AgentTraceEvent, DataBundle
from app.core.logging import get_logger
from app.tools.data import (
    fetch_institutional_trading,
    fetch_margin,
    fetch_revenue,
    fetch_stock_day,
    fetch_yahoo_summary,
)

log = get_logger(__name__)


async def data_node(state: AgentState) -> AgentState:
    ticker = state["ticker"]
    trace: list[AgentTraceEvent] = list(state.get("trace") or [])
    trace.append(AgentTraceEvent(agent="data", event="fetch_start", detail={"ticker": ticker}))

    prices, institutional, margin, revenue, fundamentals = await asyncio.gather(
        fetch_stock_day(ticker, days=120),
        fetch_institutional_trading(ticker, days=30),
        fetch_margin(ticker, days=30),
        fetch_revenue(ticker, days=420),
        fetch_yahoo_summary(ticker),
        return_exceptions=False,
    )

    bundle = DataBundle(
        prices=prices,
        institutional=institutional,
        margin=margin,
        revenue=revenue,
        fundamentals=fundamentals,
    )

    trace.append(
        AgentTraceEvent(
            agent="data",
            event="fetch_done",
            detail={
                "prices": len(prices),
                "institutional_days": len(institutional),
                "margin_days": len(margin),
                "revenue_months": len(revenue),
                "has_fundamentals": fundamentals is not None,
            },
        )
    )
    log.info("data_agent_done", ticker=ticker, bars=len(prices))

    return {**state, "data": bundle, "trace": trace}

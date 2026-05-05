from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.state import AgentState, AgentTraceEvent
from app.agents.supervisor import build_graph

router = APIRouter(prefix="/api/v1", tags=["stream"])

_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


class FinalPayload(BaseModel):
    ticker: str
    markdown: str
    citations: list[dict] = []
    indicators: dict | None = None
    generated_at: datetime


async def _stream_pipeline(ticker: str, mode: str, language: str) -> AsyncIterator[str]:
    initial: AgentState = {
        "ticker": ticker,
        "mode": mode,  # type: ignore[typeddict-item]
        "language": language,  # type: ignore[typeddict-item]
        "trace": [],
        "revisions": 0,
    }
    yield _sse("start", {"ticker": ticker, "mode": mode, "language": language})

    seen_trace: int = 0
    final_state: AgentState = initial
    try:
        async for chunk in _get_graph().astream(initial, stream_mode="values"):
            final_state = chunk  # type: ignore[assignment]
            trace_list = chunk.get("trace") or []
            while seen_trace < len(trace_list):
                evt: AgentTraceEvent = trace_list[seen_trace]
                yield _sse("trace", evt.model_dump(mode="json"))
                seen_trace += 1
    except Exception as e:
        yield _sse("error", {"message": str(e)})
        return

    report = final_state.get("report")
    analyst = final_state.get("analyst")
    if report:
        payload = FinalPayload(
            ticker=ticker,
            markdown=report.markdown,
            citations=report.citations or (analyst.citations if analyst else []),
            indicators=(
                analyst.indicators.model_dump() if analyst and analyst.indicators else None
            ),
            generated_at=datetime.utcnow(),
        )
        yield _sse("final", payload.model_dump(mode="json"))
    else:
        yield _sse("error", {"message": "no_report"})

    yield "event: done\ndata: {}\n\n"


@router.get("/analyze/stream")
async def analyze_stream(
    ticker: str = Query(..., min_length=1, max_length=12),
    mode: Literal["daily", "weekly", "on_demand"] = Query("on_demand"),
    language: Literal["zh-TW", "en"] = Query("zh-TW"),
) -> StreamingResponse:
    if not ticker.replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail="ticker must be alphanumeric")
    return StreamingResponse(
        _stream_pipeline(ticker.upper(), mode, language),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

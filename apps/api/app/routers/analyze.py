from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.agents.supervisor import run_pipeline
from app.auth import get_current_user_optional
from app.core.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["analyze"])

limiter = Limiter(key_func=get_remote_address)


class AnalyzeRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=12, examples=["2330"])
    mode: Literal["daily", "weekly", "on_demand"] = "on_demand"
    language: Literal["zh-TW", "en"] = "zh-TW"


class AnalyzeResponse(BaseModel):
    ticker: str
    mode: str
    language: str
    markdown: str
    citations: list[dict[str, Any]] = []
    indicators: dict[str, Any] | None = None
    trace: list[dict[str, Any]] = []
    generated_at: datetime


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(lambda: f"{get_settings().rate_limit_per_minute}/minute")
async def analyze(
    request: Request,
    payload: AnalyzeRequest,
    _user=Depends(get_current_user_optional),
) -> AnalyzeResponse:
    ticker = payload.ticker.strip().upper()
    if not ticker.isalnum():
        raise HTTPException(status_code=400, detail="ticker must be alphanumeric")

    state = await run_pipeline(ticker=ticker, mode=payload.mode, language=payload.language)

    report = state.get("report")
    analyst = state.get("analyst")
    if not report:
        raise HTTPException(status_code=502, detail=state.get("error") or "Pipeline failed")

    indicators = (
        analyst.indicators.model_dump() if analyst and analyst.indicators else None
    )
    trace = [t.model_dump(mode="json") for t in (state.get("trace") or [])]

    return AnalyzeResponse(
        ticker=ticker,
        mode=payload.mode,
        language=payload.language,
        markdown=report.markdown,
        citations=report.citations,
        indicators=indicators,
        trace=trace,
        generated_at=datetime.utcnow(),
    )

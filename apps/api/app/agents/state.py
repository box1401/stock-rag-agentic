from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field

from app.tools.data import (
    FundamentalSummary,
    InstitutionalRow,
    MarginRow,
    PriceBar,
    RevenueRow,
)
from app.tools.indicators import IndicatorBundle


class AgentTraceEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent: Literal["supervisor", "data", "analyst", "risk", "reporter"]
    event: str
    detail: dict[str, Any] | None = None


class DataBundle(BaseModel):
    prices: list[PriceBar] = Field(default_factory=list)
    institutional: list[InstitutionalRow] = Field(default_factory=list)
    margin: list[MarginRow] = Field(default_factory=list)
    revenue: list[RevenueRow] = Field(default_factory=list)
    fundamentals: FundamentalSummary | None = None


class AnalystOutput(BaseModel):
    headline: str
    summary: str
    bullets: list[str] = Field(default_factory=list)
    indicators: IndicatorBundle | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)


class RiskReview(BaseModel):
    pass_: bool = Field(alias="pass")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class FinalReport(BaseModel):
    markdown: str
    citations: list[dict[str, Any]] = Field(default_factory=list)


class AgentState(TypedDict, total=False):
    ticker: str
    mode: Literal["daily", "weekly", "on_demand"]
    language: Literal["zh-TW", "en"]
    data: DataBundle
    analyst: AnalystOutput
    risk: RiskReview
    revisions: int
    report: FinalReport
    trace: list[AgentTraceEvent]
    error: str

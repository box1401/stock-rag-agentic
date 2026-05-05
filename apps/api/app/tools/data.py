from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.settings import get_settings
from app.tools._http import get_json, twse_get

FINMIND_BASE = "https://api.finmindtrade.com/api/v4/data"


class PriceBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    change: float | None = None


class InstitutionalRow(BaseModel):
    date: str
    foreign_net: int = 0
    investment_trust_net: int = 0
    dealer_net: int = 0


class MarginRow(BaseModel):
    date: str
    margin_balance: int | None = None
    short_balance: int | None = None


class RevenueRow(BaseModel):
    revenue_year: int
    revenue_month: int
    revenue: int
    yoy: float | None = None


class FundamentalSummary(BaseModel):
    ticker: str
    name: str | None = None
    market: Literal["TWSE", "TPEX", "OTHER"] = "OTHER"
    pe: float | None = None
    pb: float | None = None
    dividend_yield: float | None = None


def _to_finmind_date_range(days: int) -> tuple[str, str]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


def _finmind_params(dataset: str, ticker: str, days: int) -> dict[str, str]:
    start, end = _to_finmind_date_range(days)
    params = {"dataset": dataset, "data_id": ticker, "start_date": start, "end_date": end}
    token = get_settings().finmind_token
    if token:
        params["token"] = token
    return params


async def fetch_finmind_dataset(
    dataset: str, ticker: str, days: int = 90
) -> list[dict[str, Any]]:
    """Generic FinMind fetch. Returns raw `data` array, [] on failure."""
    try:
        payload = await get_json(FINMIND_BASE, params=_finmind_params(dataset, ticker, days))
    except Exception:
        return []
    if payload.get("status") != 200:
        return []
    rows = payload.get("data") or []
    return list(rows)


async def fetch_stock_day(ticker: str, days: int = 120) -> list[PriceBar]:
    rows = await fetch_finmind_dataset("TaiwanStockPrice", ticker, days=days)
    bars: list[PriceBar] = []
    for r in rows:
        try:
            bars.append(
                PriceBar(
                    date=r["date"],
                    open=float(r["open"]),
                    high=float(r["max"]),
                    low=float(r["min"]),
                    close=float(r["close"]),
                    volume=int(r.get("Trading_Volume") or 0),
                    change=float(r.get("spread")) if r.get("spread") is not None else None,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return bars


async def fetch_institutional_trading(ticker: str, days: int = 60) -> list[InstitutionalRow]:
    rows = await fetch_finmind_dataset("TaiwanStockInstitutionalInvestorsBuySell", ticker, days=days)
    agg: dict[str, InstitutionalRow] = {}
    for r in rows:
        date = r.get("date")
        if not date:
            continue
        cur = agg.setdefault(date, InstitutionalRow(date=date))
        name = (r.get("name") or "").lower()
        net = int((r.get("buy") or 0)) - int((r.get("sell") or 0))
        if "foreign" in name:
            cur.foreign_net += net
        elif "investment" in name or "trust" in name:
            cur.investment_trust_net += net
        elif "dealer" in name:
            cur.dealer_net += net
    return sorted(agg.values(), key=lambda x: x.date, reverse=True)


async def fetch_margin(ticker: str, days: int = 60) -> list[MarginRow]:
    rows = await fetch_finmind_dataset("TaiwanStockMarginPurchaseShortSale", ticker, days=days)
    out: list[MarginRow] = []
    for r in rows:
        try:
            out.append(
                MarginRow(
                    date=r["date"],
                    margin_balance=int(r.get("MarginPurchaseTodayBalance") or 0),
                    short_balance=int(r.get("ShortSaleTodayBalance") or 0),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(out, key=lambda x: x.date, reverse=True)


async def fetch_revenue(ticker: str, days: int = 420) -> list[RevenueRow]:
    rows = await fetch_finmind_dataset("TaiwanStockMonthRevenue", ticker, days=days)
    out: list[RevenueRow] = []
    for r in rows:
        try:
            out.append(
                RevenueRow(
                    revenue_year=int(r["revenue_year"]),
                    revenue_month=int(r["revenue_month"]),
                    revenue=int(r["revenue"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    out.sort(key=lambda r: (r.revenue_year, r.revenue_month))
    for i in range(12, len(out)):
        prev = out[i - 12].revenue
        if prev:
            out[i].yoy = round((out[i].revenue - prev) / prev * 100, 2)
    return out[::-1]


async def fetch_yahoo_summary(ticker: str) -> FundamentalSummary:
    """Yahoo Finance Taiwan summary (minimal fields). Falls back to empty on failure."""
    summary = FundamentalSummary(ticker=ticker)
    yahoo_symbol = f"{ticker}.TW"
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={yahoo_symbol}"
    try:
        data = await get_json(url, timeout=10)
        result = (data.get("quoteResponse") or {}).get("result") or []
        if result:
            q = result[0]
            summary.name = q.get("shortName") or q.get("longName")
            summary.pe = q.get("trailingPE")
            summary.pb = q.get("priceToBook")
            summary.dividend_yield = q.get("trailingAnnualDividendYield")
    except Exception:
        pass
    return summary


async def fetch_twse_bwibbu(date_str: str | None = None) -> dict[str, Any]:
    """Whole-market PE / PBR / dividend yield snapshot for a given date."""
    date_str = date_str or datetime.utcnow().strftime("%Y%m%d")
    url = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d"
    return await twse_get(url, params={"date": date_str, "selectType": "ALL", "response": "json"})


class TickerSnapshot(BaseModel):
    ticker: str
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    prices: list[PriceBar] = Field(default_factory=list)
    institutional: list[InstitutionalRow] = Field(default_factory=list)
    margin: list[MarginRow] = Field(default_factory=list)
    revenue: list[RevenueRow] = Field(default_factory=list)
    fundamentals: FundamentalSummary | None = None

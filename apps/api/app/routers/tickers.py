from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.db.models import Ticker

router = APIRouter(prefix="/api/v1", tags=["tickers"])


class TickerRow(BaseModel):
    symbol: str
    name: str
    market: str
    industry: str | None = None


@router.get("/tickers", response_model=list[TickerRow])
async def list_tickers(session: AsyncSession = Depends(get_session)) -> list[TickerRow]:
    rows = (await session.execute(select(Ticker).order_by(Ticker.symbol))).scalars().all()
    return [
        TickerRow(symbol=r.symbol, name=r.name, market=r.market, industry=r.industry)
        for r in rows
    ]

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.settings import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    env: str
    time: datetime


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(status="ok", version=__version__, env=s.env, time=datetime.utcnow())

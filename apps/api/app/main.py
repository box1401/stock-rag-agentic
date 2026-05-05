from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app import __version__
from app.core.logging import configure_logging, get_logger
from app.routers import analyze as analyze_router
from app.routers import health as health_router
from app.routers import ingest as ingest_router
from app.routers import stream as stream_router
from app.routers import tickers as tickers_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("startup")
    log.info("api_startup", version=__version__)
    yield
    log.info("api_shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Compass Equity API",
        version=__version__,
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    app.state.limiter = analyze_router.limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router.router)
    app.include_router(analyze_router.router)
    app.include_router(tickers_router.router)
    app.include_router(ingest_router.router)
    app.include_router(stream_router.router)
    return app


app = create_app()

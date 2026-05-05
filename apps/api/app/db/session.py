from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import get_settings

_settings = get_settings()
_engine = create_async_engine(_settings.database_url, echo=False, pool_pre_ping=True)
sessionmaker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        yield session

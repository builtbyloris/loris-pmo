from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings


def database_engine_options(settings: Settings) -> dict[str, Any]:
    options: dict[str, Any] = {"pool_pre_ping": True}
    if make_url(settings.database_url).get_backend_name() == "postgresql":
        options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
        )
        if settings.database_ssl_mode != "disable":
            options["connect_args"] = {"ssl": settings.database_ssl_mode}
    return options


settings = get_settings()
engine = create_async_engine(settings.database_url, **database_engine_options(settings))
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session

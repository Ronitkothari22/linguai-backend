from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models import Base

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session


async def initialize_database() -> None:
    engine = get_engine()
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    except OSError as exc:
        settings = get_settings()
        host = make_url(settings.database_url).host or ""
        if host.startswith("db.") and host.endswith(".supabase.co"):
            raise RuntimeError(
                "Failed to reach the Supabase direct database host. "
                "Supabase direct connections are typically IPv6-only unless you "
                "have the IPv4 add-on. If your network is IPv4-only, replace "
                "DATABASE_URL with the Supabase Session Pooler connection string "
                "from the Connect panel."
            ) from exc
        raise RuntimeError(
            "Failed to connect to the database. Check that DATABASE_URL is "
            "reachable from this network."
        ) from exc
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Database initialization failed. Check DATABASE_URL, credentials, "
            "and database accessibility."
        ) from exc

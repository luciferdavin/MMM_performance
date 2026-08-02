"""Async SQLAlchemy engine and session factory.

Uses SQLite (aiosqlite) by default, falling back to Supabase Postgres
when a DATABASE_URL is provided in settings.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from mmm.config import get_settings
from mmm.db.models import Base


# Module-level engine and session factory (set by init_db)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str:
    """Determine the database URL based on settings.

    - If settings.database_url is set (Supabase Postgres), use it.
    - Otherwise, use SQLite at ./data/mmm.db (creating the directory if needed).
    """
    settings = get_settings()
    if settings.database_url:
        # Convert postgresql:// to postgresql+asyncpg:// for async driver
        url = settings.database_url
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url

    # Default: SQLite file
    db_path = Path("data/mmm.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def get_engine() -> AsyncEngine:
    """Get the current async engine, raising if not initialized."""
    if _engine is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the current session factory, raising if not initialized."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncSession:
    """Async context manager for database sessions.

    Usage:
        async with get_session() as db:
            result = await db.execute(select(Client))
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db(echo: bool = False) -> None:
    """Initialize the async engine and create all tables.

    Call this once at application startup.
    """
    global _engine, _session_factory

    url = get_database_url()
    _engine = create_async_engine(url, echo=echo, pool_pre_ping=True)

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create all tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close the engine. Call this at application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
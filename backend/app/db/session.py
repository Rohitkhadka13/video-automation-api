# =============================================================================
# app/db/session.py
# Async SQLAlchemy 2.0 engine + session factory.
#
# Key design decisions:
#   - create_async_engine with asyncpg driver.
#   - async_sessionmaker with expire_on_commit=False — avoids lazy-load errors
#     after a commit when the session is closed (common FastAPI gotcha).
#   - get_db() yields an AsyncSession and handles commit/rollback/close.
#   - A sync engine is provided for Alembic migrations (which cannot use async).
# =============================================================================
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Engine factory
# ---------------------------------------------------------------------------

def _build_engine(database_url: str, *, poolclass: type | None = None) -> AsyncEngine:
    """
    Create and return an AsyncEngine with production-grade pool settings.

    Args:
        database_url: asyncpg DSN string.
        poolclass:    Pass NullPool for test environments (no connection reuse).
    """
    kwargs: dict = {
        "echo": settings.DB_ECHO,
        "echo_pool": False,
        "future": True,                        # SQLAlchemy 2.0 mode
    }

    if poolclass is not None:
        # Tests: disable pooling so each test gets a fresh connection
        kwargs["poolclass"] = poolclass
    else:
        # Production: connection pool
        kwargs.update(
            {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
                "pool_recycle": settings.DB_POOL_RECYCLE,
                "pool_pre_ping": True,         # discard stale connections on checkout
            }
        )

    return create_async_engine(database_url, **kwargs)


# ---------------------------------------------------------------------------
# Engine singleton — created once at import time
# ---------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the module-level AsyncEngine, creating it on first call."""
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = _build_engine(str(settings.DATABASE_URL))
        _register_engine_events(_engine)
        logger.info(
            "db.engine.created",
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level async session factory, creating it on first call."""
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,    # ← crucial: keep attributes accessible after commit
        )
    return _session_factory


# ---------------------------------------------------------------------------
# Event listeners for observability
# ---------------------------------------------------------------------------

def _register_engine_events(engine: AsyncEngine) -> None:
    """Attach SQLAlchemy pool event listeners for logging and monitoring."""

    @event.listens_for(engine.sync_engine, "connect")
    def on_connect(dbapi_conn: object, connection_record: object) -> None:  # noqa: ANN001
        logger.debug("db.pool.connect")

    @event.listens_for(engine.sync_engine, "checkout")
    def on_checkout(dbapi_conn: object, connection_record: object, connection_proxy: object) -> None:  # noqa: ANN001
        logger.debug("db.pool.checkout")

    @event.listens_for(engine.sync_engine, "checkin")
    def on_checkin(dbapi_conn: object, connection_record: object) -> None:  # noqa: ANN001
        logger.debug("db.pool.checkin")


# ---------------------------------------------------------------------------
# Dependency — injected into FastAPI route handlers via Depends(get_db)
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.

    Lifecycle:
      1. Acquire session from pool.
      2. Yield to route handler.
      3a. If no exception: commit.
      3b. If exception: rollback.
      4. Always close the session (returns connection to pool).

    Usage in endpoints:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Context manager — for use outside FastAPI request context (Celery tasks, scripts)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager providing a database session.
    Use this in Celery tasks and standalone scripts where FastAPI Depends()
    is not available.

    Usage:
        async with get_db_context() as db:
            result = await db.execute(select(User))
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Test utilities — called from tests/conftest.py
# ---------------------------------------------------------------------------

def build_test_engine(test_database_url: str) -> AsyncEngine:
    """
    Build an engine for test runs using NullPool (no connection pooling).
    Each test function gets its own connection — no state leaks between tests.
    """
    return _build_engine(test_database_url, poolclass=NullPool)


def build_test_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Build a session factory bound to the test engine."""
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


# ---------------------------------------------------------------------------
# Lifecycle helpers — called from app lifespan in main.py
# ---------------------------------------------------------------------------

async def open_db_connection() -> None:
    """Warm up the connection pool at application startup."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)   # no-op — just exercises pool checkout
    logger.info("db.connection.pool.warmed_up")


async def close_db_connection() -> None:
    """Dispose of all connections in the pool at application shutdown."""
    global _engine, _session_factory  # noqa: PLW0603
    if _engine is not None:
        await _engine.dispose()
        logger.info("db.connection.pool.disposed")
        _engine = None
        _session_factory = None


async def check_db_health() -> bool:
    """
    Execute a trivial query to verify DB connectivity.
    Used by the /health endpoint.
    """
    from sqlalchemy import text  # local import avoids circular at module load

    try:
        async with get_engine().begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("db.health.check.failed", error=str(exc))
        return False
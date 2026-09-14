"""
app/database/shared_engine.py

Singleton async SQLAlchemy engine for use by LangGraph tool functions.

Problem this solves:
    Each tool call (product_tools, order_tools, memory) previously called
    create_async_engine() + engine.dispose() per invocation, creating 5-8
    engine instances per conversation turn and adding ~200-400ms latency.

Usage:
    from app.database.shared_engine import get_shared_session

    async def my_tool_async():
        async with get_shared_session() as session:
            result = await session.execute(...)
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.logging import get_logger

logger = get_logger(__name__)

_engine = None
_session_factory = None
_lock = asyncio.Lock()


def _build_engine():
    """Build the shared engine (called once)."""
    from app.config.settings import get_settings
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    return engine


def get_engine():
    """Return the shared engine, creating it on first call (thread-safe via module-level init)."""
    global _engine, _session_factory
    if _engine is None:
        _engine = _build_engine()
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)
        logger.info("Shared async engine initialized")
    return _engine


def get_session_factory():
    """Return the shared session factory."""
    global _session_factory
    if _session_factory is None:
        get_engine()  # initializes both
    return _session_factory


@asynccontextmanager
async def get_shared_session():
    """
    Async context manager yielding a database session from the shared pool.

    Usage:
        async with get_shared_session() as session:
            result = await session.execute(select(Product))
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def run_in_thread(coro):
    """
    Run an async coroutine from a synchronous context (inside tool functions
    that are called from LangGraph's ThreadPoolExecutor).

    Handles the case where an event loop is already running (uvicorn) by
    submitting to a fresh thread with its own event loop.
    """
    import concurrent.futures
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)

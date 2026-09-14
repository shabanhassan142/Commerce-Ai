"""
app/database/session.py

Async SQLAlchemy session factory and database dependency.

Uses:
  - create_async_engine  (asyncpg driver)
  - async_sessionmaker   (creates AsyncSession instances)
  - AsyncSession         (injected into route handlers via get_db())

Connection pooling is configured for production workloads.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,          # Log SQL queries in development
    pool_size=10,                 # Number of connections to maintain
    max_overflow=20,              # Extra connections when pool is exhausted
    pool_pre_ping=True,           # Verify connections before use (handles stale connections)
    pool_recycle=3600,            # Recycle connections every 1 hour
)

# ── Session Factory ───────────────────────────────────────────────────────────

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,       # Keep objects accessible after commit
    autocommit=False,
    autoflush=False,
)


# ── FastAPI Dependency ────────────────────────────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides an async database session.
    Automatically commits on success and rolls back on exception.

    Usage in route handlers:
        @router.get("/example")
        async def my_route(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Database Health Check ─────────────────────────────────────────────────────

async def check_database_connection() -> bool:
    """
    Attempts a lightweight database ping.
    Used by the health check endpoint and startup event.

    Returns:
        True if the database is reachable, False otherwise.
    """
    from sqlalchemy import text

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        return True
    except Exception as exc:
        logger.error(f"Database connection failed: {exc}")
        return False

"""
app/api/deps.py

Shared FastAPI dependencies used across all API routers.

Centralizing dependencies here prevents circular imports and
makes them easy to mock in tests.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency.
    Injected into route handlers via Depends(get_db).

    Auto-commits on success, auto-rollbacks on exceptions.
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

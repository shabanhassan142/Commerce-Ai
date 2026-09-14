"""
tests/test_auth.py

Integration tests for the authentication API.
Tests all 5 auth endpoints using an in-memory test database.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.main import app
from app.api.deps import get_db

# Use SQLite in-memory for tests (no PostgreSQL required)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine with SQLite."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Provide a clean session and fresh database schema for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        bind=test_engine, expire_on_commit=False
    )
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    """
    Async HTTP client with overridden DB dependency.
    Uses the test SQLite DB instead of PostgreSQL.
    """
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Test Data ─────────────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "full_name": "Alice Johnson",
    "email": "alice@test.com",
    "password": "SecurePass123!",
    "role": "customer",
}

LOGIN_PAYLOAD = {
    "email": "alice@test.com",
    "password": "SecurePass123!",
}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        """New user can register successfully."""
        response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "tokens" in data["data"]
        assert data["data"]["tokens"]["access_token"]
        assert data["data"]["tokens"]["refresh_token"]
        assert data["data"]["user"]["email"] == "alice@test.com"

    async def test_register_duplicate_email(self, client: AsyncClient):
        """Cannot register with an already-used email."""
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        response = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        assert response.status_code == 409
        assert response.json()["success"] is False

    async def test_register_weak_password(self, client: AsyncClient):
        """Weak password is rejected with 422."""
        payload = {**REGISTER_PAYLOAD, "email": "bob@test.com", "password": "weak"}
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        """Valid credentials return tokens."""
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        response = await client.post("/api/v1/auth/login", json=LOGIN_PAYLOAD)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["tokens"]["access_token"]

    async def test_login_wrong_password(self, client: AsyncClient):
        """Wrong password returns 401."""
        await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        response = await client.post(
            "/api/v1/auth/login",
            json={**LOGIN_PAYLOAD, "password": "WrongPass123!"},
        )
        assert response.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        """Unknown email returns 401 (not 404 — prevents enumeration)."""
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@test.com", "password": "Pass123!"},
        )
        assert response.status_code == 401


class TestProtectedRoutes:
    async def test_me_with_valid_token(self, client: AsyncClient):
        """Authenticated user can access /me."""
        payload = {
            "full_name": "Me Test User",
            "email": "me_test_user@test.com",
            "password": "SecurePass123!",
            "role": "customer",
        }
        reg = await client.post("/api/v1/auth/register", json=payload)
        token = reg.json()["data"]["tokens"]["access_token"]

        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "me_test_user@test.com"

    async def test_me_without_token(self, client: AsyncClient):
        """Unauthenticated request to /me returns 401."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_with_invalid_token(self, client: AsyncClient):
        """Invalid token returns 401."""
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalidtoken"},
        )
        assert response.status_code == 401


class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient):
        """Valid refresh token issues a new access token."""
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        refresh_token = reg.json()["data"]["tokens"]["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert response.json()["data"]["access_token"]

    async def test_refresh_with_access_token_fails(self, client: AsyncClient):
        """Access token cannot be used as refresh token."""
        reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
        access_token = reg.json()["data"]["tokens"]["access_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert response.status_code == 401


class TestHealth:
    async def test_health_check(self, client: AsyncClient):
        """Health endpoint returns system status."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "services" in data["data"]

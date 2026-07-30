"""
tests/conftest.py

Pytest fixtures for the authentication test suite.

Architecture:
    - Uses SQLite (aiosqlite) in-memory database for speed and isolation.
    - Each test function gets a fresh DB (function scope).
    - Overrides the `get_db` dependency so tests never touch PostgreSQL.
    - Provides ready-made user fixtures for common test patterns.
"""
import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole

# ── SQLite in-memory test database ───────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh in-memory SQLite database for each test function.

    Yields an AsyncSession connected to that database.
    All tables are created on startup and dropped (implicitly) when
    the in-memory DB is destroyed after the test.
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(test_db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    AsyncClient with the FastAPI app, using the test database.

    The `get_db` dependency is overridden to return our test session.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        try:
            yield test_db
            await test_db.commit()
        except Exception:
            await test_db.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()


# ── User Fixtures ─────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def public_user(test_db: AsyncSession) -> User:
    """A persisted PUBLIC_USER for use in authenticated tests."""
    user = User(
        full_name="Test User",
        email="testuser@example.com",
        hashed_password=hash_password("TestPass1"),
        role=UserRole.PUBLIC_USER,
        is_active=True,
        is_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(test_db: AsyncSession) -> User:
    """A persisted ADMIN user for RBAC tests."""
    user = User(
        full_name="Admin User",
        email="admin@example.com",
        hashed_password=hash_password("AdminPass1"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def traffic_controller_user(test_db: AsyncSession) -> User:
    """A persisted TRAFFIC_CONTROLLER user for RBAC tests."""
    user = User(
        full_name="Traffic Controller",
        email="controller@example.com",
        hashed_password=hash_password("ControllerPass1"),
        role=UserRole.TRAFFIC_CONTROLLER,
        is_active=True,
        is_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def inactive_user(test_db: AsyncSession) -> User:
    """A persisted inactive user for deactivation tests."""
    user = User(
        full_name="Inactive User",
        email="inactive@example.com",
        hashed_password=hash_password("InactivePass1"),
        role=UserRole.PUBLIC_USER,
        is_active=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


# ── Token Helpers ─────────────────────────────────────────────────────────────

def make_auth_headers(token: str) -> dict[str, str]:
    """Return Authorization headers for a Bearer token."""
    return {"Authorization": f"Bearer {token}"}


async def login_user(client: AsyncClient, email: str, password: str) -> str:
    """Login a user and return the access token string."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    return response.json()["access_token"]

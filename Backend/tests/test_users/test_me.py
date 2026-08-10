"""
tests/test_users/test_me.py

Tests for GET /api/v1/users/me and PUT /api/v1/users/me endpoints.
"""
import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import login_user, make_auth_headers


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, public_user: User) -> None:
    """Authenticated user should receive their own profile."""
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.get("/api/v1/users/me", headers=make_auth_headers(token))

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["full_name"] == "Test User"
    assert data["role"] == "PUBLIC_USER"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_me_without_token_fails(client: AsyncClient) -> None:
    """GET /users/me without Authorization header should return 403."""
    response = await client.get("/api/v1/users/me")
    # FastAPI HTTPBearer returns 403 when no credentials are provided
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_me_invalid_token_fails(client: AsyncClient) -> None:
    """Invalid JWT should return 401."""
    response = await client.get(
        "/api/v1/users/me",
        headers=make_auth_headers("invalid.jwt.token"),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_me_full_name(client: AsyncClient, public_user: User) -> None:
    """User should be able to update their full_name."""
    token = await login_user(client, "testuser@example.com", "TestPass1")

    response = await client.put(
        "/api/v1/users/me",
        headers=make_auth_headers(token),
        json={"full_name": "Jane Smith Updated"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Jane Smith Updated"


@pytest.mark.asyncio
async def test_update_me_password(client: AsyncClient, public_user: User) -> None:
    """User should be able to change their password and login with the new one."""
    token = await login_user(client, "testuser@example.com", "TestPass1")

    # Change password
    update_resp = await client.put(
        "/api/v1/users/me",
        headers=make_auth_headers(token),
        json={"password": "NewValidPass1"},
    )
    assert update_resp.status_code == 200

    # Login with new password should succeed
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "NewValidPass1"},
    )
    assert login_resp.status_code == 200

    # Login with old password should now fail
    old_login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "TestPass1"},
    )
    assert old_login_resp.status_code == 401


@pytest.mark.asyncio
async def test_update_me_empty_body_returns_unchanged(client: AsyncClient, public_user: User) -> None:
    """PUT with empty body should return unchanged profile (no crash)."""
    token = await login_user(client, "testuser@example.com", "TestPass1")

    response = await client.put(
        "/api/v1/users/me",
        headers=make_auth_headers(token),
        json={},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "testuser@example.com"


@pytest.mark.asyncio
async def test_update_me_weak_password_rejected(client: AsyncClient, public_user: User) -> None:
    """Weak password in update should return 422."""
    token = await login_user(client, "testuser@example.com", "TestPass1")

    response = await client.put(
        "/api/v1/users/me",
        headers=make_auth_headers(token),
        json={"password": "weakpassword"},  # No digit
    )
    assert response.status_code == 422

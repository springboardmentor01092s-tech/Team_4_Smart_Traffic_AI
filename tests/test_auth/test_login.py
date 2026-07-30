"""
tests/test_auth/test_login.py

Tests for POST /api/v1/auth/login and POST /api/v1/auth/logout endpoints.
"""
import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, public_user: User) -> None:
    """Valid credentials should return a JWT access token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "TestPass1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert len(data["access_token"]) > 20  # Should be a non-trivial JWT string


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, public_user: User) -> None:
    """Wrong password should return 401 Unauthorized."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "WrongPass1"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient) -> None:
    """Login with email not in DB should return 401 (not 404, to prevent enumeration)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "SomePass1"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_inactive_account(client: AsyncClient, inactive_user: User) -> None:
    """Inactive user should receive 403 Forbidden."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "InactivePass1"},
    )
    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCOUNT_INACTIVE"


@pytest.mark.asyncio
async def test_login_invalid_email_format(client: AsyncClient) -> None:
    """Malformed email in login should return 422."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "bad-email", "password": "SomePass1"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_logout_returns_200(client: AsyncClient) -> None:
    """Logout endpoint should return 200 OK with acknowledgement message."""
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_login_then_access_protected_route(client: AsyncClient, public_user: User) -> None:
    """After login, the token should grant access to protected routes."""
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testuser@example.com", "password": "TestPass1"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "testuser@example.com"

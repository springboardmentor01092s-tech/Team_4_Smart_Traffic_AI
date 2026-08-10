"""
tests/test_auth/test_register.py

Tests for POST /api/v1/auth/register endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    """A new user with valid data should be created with PUBLIC_USER role."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password": "ValidPass1",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "jane@example.com"
    assert data["full_name"] == "Jane Doe"
    assert data["role"] == "PUBLIC_USER"
    assert data["is_active"] is True
    assert "id" in data
    assert "hashed_password" not in data  # MUST never be returned


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client: AsyncClient) -> None:
    """Registering with an already-used email should return 409 Conflict."""
    payload = {
        "full_name": "First User",
        "email": "duplicate@example.com",
        "password": "ValidPass1",
    }
    # First registration
    response1 = await client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == 201

    # Second registration with same email
    payload["full_name"] = "Second User"
    response2 = await client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password_rejected(client: AsyncClient) -> None:
    """Password with no digits should fail Pydantic validation (422)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password": "nodigitpassword",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password_rejected(client: AsyncClient) -> None:
    """Password shorter than 8 characters should fail validation."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Jane Doe",
            "email": "jane@example.com",
            "password": "Ab1",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_rejected(client: AsyncClient) -> None:
    """Malformed email address should fail Pydantic EmailStr validation."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Jane Doe",
            "email": "not-an-email",
            "password": "ValidPass1",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_fields_rejected(client: AsyncClient) -> None:
    """Request with missing required fields should return 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "jane@example.com"},  # Missing full_name and password
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_email_normalized_to_lowercase(client: AsyncClient) -> None:
    """Email should be normalized to lowercase during registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Jane Doe",
            "email": "JANE@EXAMPLE.COM",
            "password": "ValidPass1",
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "jane@example.com"

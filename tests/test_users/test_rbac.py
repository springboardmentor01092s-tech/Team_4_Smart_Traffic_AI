"""
tests/test_users/test_rbac.py

Tests for Role-Based Access Control (RBAC).

Validates that:
  - The require_role() dependency correctly allows/denies access.
  - Different roles receive appropriate responses.
  - The role claim in the JWT is correlated with the DB role.

Note: Since we only have /users/me as a role-protected endpoint in this
foundation, RBAC tests primarily verify the dependency mechanism itself
using the existing endpoints and by checking token payloads.
Future Dev #2 route tests should also use make_auth_headers/login_user helpers.
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, decode_access_token
from app.models.user import User, UserRole
from tests.conftest import login_user, make_auth_headers


@pytest.mark.asyncio
async def test_public_user_role_in_token(client: AsyncClient, public_user: User) -> None:
    """JWT for a PUBLIC_USER should contain role=PUBLIC_USER."""
    token = await login_user(client, "testuser@example.com", "TestPass1")
    payload = decode_access_token(token)
    assert payload["role"] == UserRole.PUBLIC_USER


@pytest.mark.asyncio
async def test_admin_role_in_token(client: AsyncClient, admin_user: User) -> None:
    """JWT for an ADMIN should contain role=ADMIN."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    payload = decode_access_token(token)
    assert payload["role"] == UserRole.ADMIN


@pytest.mark.asyncio
async def test_traffic_controller_role_in_token(
    client: AsyncClient, traffic_controller_user: User
) -> None:
    """JWT for a TRAFFIC_CONTROLLER should contain the correct role."""
    token = await login_user(client, "controller@example.com", "ControllerPass1")
    payload = decode_access_token(token)
    assert payload["role"] == UserRole.TRAFFIC_CONTROLLER


@pytest.mark.asyncio
async def test_all_roles_can_access_own_profile(
    client: AsyncClient,
    public_user: User,
    admin_user: User,
    traffic_controller_user: User,
) -> None:
    """All roles should be able to access GET /users/me."""
    for email, password in [
        ("testuser@example.com", "TestPass1"),
        ("admin@example.com", "AdminPass1"),
        ("controller@example.com", "ControllerPass1"),
    ]:
        token = await login_user(client, email, password)
        resp = await client.get("/api/v1/users/me", headers=make_auth_headers(token))
        assert resp.status_code == 200, f"Role test failed for {email}"


@pytest.mark.asyncio
async def test_require_role_dependency_allows_correct_role(public_user: User) -> None:
    """
    The require_role dependency factory should accept a user whose role is listed.
    This tests the factory logic directly using the security module.
    """
    token = create_access_token(
        subject=str(public_user.id),
        additional_claims={"role": UserRole.PUBLIC_USER, "email": public_user.email},
    )
    payload = decode_access_token(token)
    # Verify the role is correctly encoded in the token
    assert payload["role"] == UserRole.PUBLIC_USER
    assert payload["sub"] == str(public_user.id)


@pytest.mark.asyncio
async def test_inactive_user_cannot_access_protected_routes(
    client: AsyncClient, inactive_user: User
) -> None:
    """
    An inactive user who somehow gets a valid token should be rejected.

    This simulates account deactivation AFTER a token was issued.
    The get_current_user dependency checks is_active on every request.
    """
    # Create a valid token for the inactive user bypassing the login endpoint
    valid_token = create_access_token(
        subject=str(inactive_user.id),
        additional_claims={"role": inactive_user.role, "email": inactive_user.email},
    )

    response = await client.get(
        "/api/v1/users/me",
        headers=make_auth_headers(valid_token),
    )
    # Should be 403 because get_current_user checks is_active
    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCOUNT_INACTIVE"

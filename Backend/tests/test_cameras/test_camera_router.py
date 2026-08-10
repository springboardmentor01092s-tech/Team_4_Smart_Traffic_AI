"""
tests/test_cameras/test_camera_router.py

Integration (router-level) tests for the Traffic Cameras endpoints.

Uses the `client` fixture (AsyncClient + overridden get_db → SQLite).
Tests the full HTTP stack: router → service → repository → SQLite.

Coverage:
  - GET /api/v1/cameras         (200, empty list, status filter)
  - GET /api/v1/cameras/{id}    (200, 404)
  - POST /api/v1/cameras        (201, 422 validation, 401 no token, 403 wrong role)
  - PUT /api/v1/cameras/{id}    (200, 404, 422, 403 wrong role)
  - DELETE /api/v1/cameras/{id} (204, 404, 403 wrong role)
  - RBAC matrix: PUBLIC_USER=403, TRAFFIC_CONTROLLER=403, ADMIN=201 for POST
  - Soft-delete visibility: GET after DELETE returns 404
"""
import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import login_user, make_auth_headers

BASE = "/api/v1/cameras"

# ── Shared payload ────────────────────────────────────────────────────────────

VALID_CAMERA_PAYLOAD = {
    "name": "Integration Test Camera",
    "location_name": "Test Road, Sector 7",
    "latitude": 28.6139,
    "longitude": 77.2090,
    "status": "ACTIVE",
    "description": "Created by integration test",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

async def create_camera_as_admin(client: AsyncClient, admin_user: User) -> dict:
    """Login as admin and POST a camera. Returns the response JSON dict."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        BASE,
        json=VALID_CAMERA_PAYLOAD,
        headers=make_auth_headers(token),
    )
    assert response.status_code == 201, f"Failed to create camera: {response.text}"
    return response.json()


# ── GET /cameras (list) ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_cameras_empty(client: AsyncClient, public_user: User) -> None:
    """GET /cameras with no cameras in DB should return an empty list."""
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.get(BASE, headers=make_auth_headers(token))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_cameras_returns_created(
    client: AsyncClient, admin_user: User, public_user: User
) -> None:
    """GET /cameras should return a camera after it has been created."""
    created = await create_camera_as_admin(client, admin_user)
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.get(BASE, headers=make_auth_headers(token))
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    ids = [c["id"] for c in data]
    assert created["id"] in ids


@pytest.mark.asyncio
async def test_list_cameras_status_filter(
    client: AsyncClient, admin_user: User
) -> None:
    """GET /cameras?status=INACTIVE should return only INACTIVE cameras."""
    token = await login_user(client, "admin@example.com", "AdminPass1")

    # Create ACTIVE camera
    await client.post(
        BASE,
        json={**VALID_CAMERA_PAYLOAD, "status": "ACTIVE", "name": "Active Cam"},
        headers=make_auth_headers(token),
    )
    # Create INACTIVE camera
    inactive_resp = await client.post(
        BASE,
        json={**VALID_CAMERA_PAYLOAD, "status": "INACTIVE", "name": "Inactive Cam"},
        headers=make_auth_headers(token),
    )
    inactive_id = inactive_resp.json()["id"]

    response = await client.get(
        f"{BASE}?status=INACTIVE",
        headers=make_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert all(c["status"] == "INACTIVE" for c in data)
    assert any(c["id"] == inactive_id for c in data)


@pytest.mark.asyncio
async def test_list_cameras_requires_auth(client: AsyncClient) -> None:
    """GET /cameras without a token should return 403 (HTTPBearer auto_error)."""
    response = await client.get(BASE)
    assert response.status_code == 403


# ── GET /cameras/{id} ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_camera_by_id_success(
    client: AsyncClient, admin_user: User, public_user: User
) -> None:
    """GET /cameras/{id} should return the correct camera detail."""
    created = await create_camera_as_admin(client, admin_user)
    camera_id = created["id"]

    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.get(f"{BASE}/{camera_id}", headers=make_auth_headers(token))

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == camera_id
    assert data["name"] == VALID_CAMERA_PAYLOAD["name"]
    assert data["latitude"] == VALID_CAMERA_PAYLOAD["latitude"]
    assert data["longitude"] == VALID_CAMERA_PAYLOAD["longitude"]
    assert "deleted_at" not in data  # Must never be exposed


@pytest.mark.asyncio
async def test_get_camera_by_id_not_found(
    client: AsyncClient, public_user: User
) -> None:
    """GET /cameras/{id} for a non-existent UUID should return 404."""
    import uuid
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.get(
        f"{BASE}/{uuid.uuid4()}",
        headers=make_auth_headers(token),
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "CAMERA_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_camera_returns_404_after_delete(
    client: AsyncClient, admin_user: User
) -> None:
    """GET /cameras/{id} should return 404 after the camera has been soft-deleted."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    created = await create_camera_as_admin(client, admin_user)
    camera_id = created["id"]

    # Delete
    del_resp = await client.delete(
        f"{BASE}/{camera_id}", headers=make_auth_headers(token)
    )
    assert del_resp.status_code == 204

    # Fetch — should now be 404
    get_resp = await client.get(f"{BASE}/{camera_id}", headers=make_auth_headers(token))
    assert get_resp.status_code == 404


# ── POST /cameras ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_camera_admin_success(
    client: AsyncClient, admin_user: User
) -> None:
    """POST /cameras by ADMIN should create a camera and return 201."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        BASE,
        json=VALID_CAMERA_PAYLOAD,
        headers=make_auth_headers(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == VALID_CAMERA_PAYLOAD["name"]
    assert data["status"] == "ACTIVE"
    assert "id" in data
    assert "deleted_at" not in data


@pytest.mark.asyncio
async def test_create_camera_without_token_returns_403(client: AsyncClient) -> None:
    """POST /cameras without Authorization header should return 403."""
    response = await client.post(BASE, json=VALID_CAMERA_PAYLOAD)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_camera_invalid_token_returns_401(client: AsyncClient) -> None:
    """POST /cameras with an invalid JWT should return 401."""
    response = await client.post(
        BASE,
        json=VALID_CAMERA_PAYLOAD,
        headers=make_auth_headers("not.a.jwt"),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_camera_public_user_returns_403(
    client: AsyncClient, public_user: User
) -> None:
    """POST /cameras by PUBLIC_USER should be rejected with 403."""
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.post(
        BASE,
        json=VALID_CAMERA_PAYLOAD,
        headers=make_auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_camera_traffic_controller_returns_403(
    client: AsyncClient, traffic_controller_user: User
) -> None:
    """POST /cameras by TRAFFIC_CONTROLLER should be rejected with 403."""
    token = await login_user(client, "controller@example.com", "ControllerPass1")
    response = await client.post(
        BASE,
        json=VALID_CAMERA_PAYLOAD,
        headers=make_auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_camera_missing_name_returns_422(
    client: AsyncClient, admin_user: User
) -> None:
    """POST /cameras without 'name' field should return 422."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    payload = {k: v for k, v in VALID_CAMERA_PAYLOAD.items() if k != "name"}
    response = await client.post(BASE, json=payload, headers=make_auth_headers(token))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_camera_invalid_latitude_returns_422(
    client: AsyncClient, admin_user: User
) -> None:
    """POST /cameras with latitude > 90 should return 422."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        BASE,
        json={**VALID_CAMERA_PAYLOAD, "latitude": 91.0},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_camera_invalid_longitude_returns_422(
    client: AsyncClient, admin_user: User
) -> None:
    """POST /cameras with longitude < -180 should return 422."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        BASE,
        json={**VALID_CAMERA_PAYLOAD, "longitude": -181.0},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_camera_invalid_status_returns_422(
    client: AsyncClient, admin_user: User
) -> None:
    """POST /cameras with an unknown status value should return 422."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        BASE,
        json={**VALID_CAMERA_PAYLOAD, "status": "FLYING"},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_camera_name_too_short_returns_422(
    client: AsyncClient, admin_user: User
) -> None:
    """POST /cameras with name shorter than 2 chars should return 422."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        BASE,
        json={**VALID_CAMERA_PAYLOAD, "name": "A"},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_camera_description_too_long_returns_422(
    client: AsyncClient, admin_user: User
) -> None:
    """POST /cameras with description exceeding 500 chars should return 422."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        BASE,
        json={**VALID_CAMERA_PAYLOAD, "description": "x" * 501},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 422


# ── PUT /cameras/{id} ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_camera_success(client: AsyncClient, admin_user: User) -> None:
    """PUT /cameras/{id} by ADMIN should update the camera and return 200."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    created = await create_camera_as_admin(client, admin_user)
    camera_id = created["id"]

    response = await client.put(
        f"{BASE}/{camera_id}",
        json={"name": "Updated Camera Name", "status": "MAINTENANCE"},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Camera Name"
    assert data["status"] == "MAINTENANCE"
    # Unchanged field preserved
    assert data["latitude"] == VALID_CAMERA_PAYLOAD["latitude"]


@pytest.mark.asyncio
async def test_update_camera_not_found_returns_404(
    client: AsyncClient, admin_user: User
) -> None:
    """PUT /cameras/{non-existent-id} should return 404."""
    import uuid
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.put(
        f"{BASE}/{uuid.uuid4()}",
        json={"name": "Ghost Camera"},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_camera_public_user_returns_403(
    client: AsyncClient, admin_user: User, public_user: User
) -> None:
    """PUT /cameras/{id} by PUBLIC_USER should be rejected with 403."""
    created = await create_camera_as_admin(client, admin_user)
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.put(
        f"{BASE}/{created['id']}",
        json={"name": "Hacked"},
        headers=make_auth_headers(token),
    )
    assert response.status_code == 403


# ── DELETE /cameras/{id} ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_camera_admin_success(client: AsyncClient, admin_user: User) -> None:
    """DELETE /cameras/{id} by ADMIN should return 204."""
    token = await login_user(client, "admin@example.com", "AdminPass1")
    created = await create_camera_as_admin(client, admin_user)

    response = await client.delete(
        f"{BASE}/{created['id']}", headers=make_auth_headers(token)
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_camera_not_found_returns_404(
    client: AsyncClient, admin_user: User
) -> None:
    """DELETE /cameras/{non-existent-id} should return 404."""
    import uuid
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.delete(
        f"{BASE}/{uuid.uuid4()}", headers=make_auth_headers(token)
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_camera_public_user_returns_403(
    client: AsyncClient, admin_user: User, public_user: User
) -> None:
    """DELETE /cameras/{id} by PUBLIC_USER should be rejected with 403."""
    created = await create_camera_as_admin(client, admin_user)
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.delete(
        f"{BASE}/{created['id']}", headers=make_auth_headers(token)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_camera_traffic_controller_returns_403(
    client: AsyncClient, admin_user: User, traffic_controller_user: User
) -> None:
    """DELETE /cameras/{id} by TRAFFIC_CONTROLLER should be rejected with 403."""
    created = await create_camera_as_admin(client, admin_user)
    token = await login_user(client, "controller@example.com", "ControllerPass1")
    response = await client.delete(
        f"{BASE}/{created['id']}", headers=make_auth_headers(token)
    )
    assert response.status_code == 403


# ── RBAC matrix ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rbac_matrix_create_camera(
    client: AsyncClient,
    admin_user: User,
    traffic_controller_user: User,
    public_user: User,
) -> None:
    """Verify the full RBAC matrix for POST /cameras."""
    # PUBLIC_USER → 403
    pub_token = await login_user(client, "testuser@example.com", "TestPass1")
    r1 = await client.post(BASE, json=VALID_CAMERA_PAYLOAD, headers=make_auth_headers(pub_token))
    assert r1.status_code == 403

    # TRAFFIC_CONTROLLER → 403
    tc_token = await login_user(client, "controller@example.com", "ControllerPass1")
    r2 = await client.post(BASE, json=VALID_CAMERA_PAYLOAD, headers=make_auth_headers(tc_token))
    assert r2.status_code == 403

    # ADMIN → 201
    adm_token = await login_user(client, "admin@example.com", "AdminPass1")
    r3 = await client.post(BASE, json=VALID_CAMERA_PAYLOAD, headers=make_auth_headers(adm_token))
    assert r3.status_code == 201


# ── Soft-delete visibility workflow ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_soft_delete_visibility_workflow(
    client: AsyncClient, admin_user: User, public_user: User
) -> None:
    """
    Integration workflow:
      1. Admin creates camera.
      2. Public user can see it in list and by id.
      3. Admin deletes it.
      4. Camera disappears from list.
      5. Get by id returns 404.
    """
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    pub_token = await login_user(client, "testuser@example.com", "TestPass1")

    # Step 1: Create
    create_resp = await client.post(
        BASE, json=VALID_CAMERA_PAYLOAD, headers=make_auth_headers(admin_token)
    )
    assert create_resp.status_code == 201
    camera_id = create_resp.json()["id"]

    # Step 2: List includes it
    list_resp = await client.get(BASE, headers=make_auth_headers(pub_token))
    assert any(c["id"] == camera_id for c in list_resp.json())

    # Step 2b: Get by id works
    get_resp = await client.get(f"{BASE}/{camera_id}", headers=make_auth_headers(pub_token))
    assert get_resp.status_code == 200

    # Step 3: Admin soft-deletes
    del_resp = await client.delete(
        f"{BASE}/{camera_id}", headers=make_auth_headers(admin_token)
    )
    assert del_resp.status_code == 204

    # Step 4: List no longer includes it
    list_resp2 = await client.get(BASE, headers=make_auth_headers(pub_token))
    assert not any(c["id"] == camera_id for c in list_resp2.json())

    # Step 5: Get by id now returns 404
    get_resp2 = await client.get(f"{BASE}/{camera_id}", headers=make_auth_headers(pub_token))
    assert get_resp2.status_code == 404

"""
tests/test_routes/test_route_router.py

Integration tests for the Routes HTTP API endpoints.

Uses the httpx AsyncClient with the in-memory SQLite test DB.
Each test is function-scoped for full isolation.

Coverage:
  - GET  /routes                        → 200, pagination, is_active filter
  - GET  /routes/{id}                   → 200, 404 (nonexistent), 404 (soft-deleted)
  - GET  /routes/{id}/traffic           → 200, 404
  - POST /routes                        → 201, 403 (wrong role), 422 (bad data)
  - PUT  /routes/{id}                   → 200, 404, 403
  - POST /routes/{id}/segments          → 201, 404, 409, 403
  - DELETE /routes/{id}/segments/{sid}  → 204, 404
  - DELETE /routes/{id}                 → 204, 404, 403
  - RBAC matrix: PUBLIC_USER cannot write; ADMIN can write
  - Standard error envelope shape for 4xx responses
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.segment import TrafficSegment
from tests.conftest import login_user, make_auth_headers


# ── Fixtures ──────────────────────────────────────────────────────────────────

async def _create_segment(db: AsyncSession) -> TrafficSegment:
    seg = TrafficSegment(
        name=f"Seg-{uuid.uuid4().hex[:6]}",
        start_point="A",
        end_point="B",
        start_latitude=1.0,
        start_longitude=1.0,
        end_latitude=2.0,
        end_longitude=2.0,
        length_km=1.0,
        speed_limit_kmh=60,
    )
    db.add(seg)
    await db.commit()
    await db.refresh(seg)
    return seg


ROUTE_PAYLOAD = {
    "name": "Test Route",
    "origin_name": "City A",
    "destination_name": "City B",
    "total_distance_km": 25.0,
}


# ── Authentication guard tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_routes_requires_auth(client: AsyncClient) -> None:
    # App returns 403 (not 401) when no Authorization header is provided.
    # This is the established behavior of get_current_user across all modules.
    response = await client.get("/api/v1/routes")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_route_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/routes", json=ROUTE_PAYLOAD)
    assert response.status_code in (401, 403)


# ── RBAC tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_public_user_cannot_create_route(
    client: AsyncClient, public_user, admin_user
) -> None:
    admin_token = await login_user(client, admin_user.email, "AdminPass1")
    pub_token = await login_user(client, public_user.email, "TestPass1")

    # Admin creates a route first (needed for some tests).
    response = await client.post(
        "/api/v1/routes",
        json=ROUTE_PAYLOAD,
        headers=make_auth_headers(pub_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_route(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    response = await client.post(
        "/api/v1/routes",
        json=ROUTE_PAYLOAD,
        headers=make_auth_headers(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Route"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_public_user_can_read_routes(client: AsyncClient, public_user) -> None:
    token = await login_user(client, public_user.email, "TestPass1")
    response = await client.get("/api/v1/routes", headers=make_auth_headers(token))
    assert response.status_code == 200


# ── GET /routes tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_routes_returns_created_route(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)

    create_resp = await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)
    assert create_resp.status_code == 201
    route_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/routes", headers=headers)
    assert list_resp.status_code == 200
    ids = [r["id"] for r in list_resp.json()]
    assert route_id in ids


@pytest.mark.asyncio
async def test_list_routes_soft_deleted_excluded(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)

    create_resp = await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)
    route_id = create_resp.json()["id"]
    await client.delete(f"/api/v1/routes/{route_id}", headers=headers)

    list_resp = await client.get("/api/v1/routes", headers=headers)
    ids = [r["id"] for r in list_resp.json()]
    assert route_id not in ids


@pytest.mark.asyncio
async def test_list_routes_is_active_filter(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)

    r1 = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()
    await client.put(f"/api/v1/routes/{r1['id']}", json={"is_active": False}, headers=headers)

    active_resp = await client.get("/api/v1/routes?is_active=true", headers=headers)
    inactive_resp = await client.get("/api/v1/routes?is_active=false", headers=headers)

    active_ids = [r["id"] for r in active_resp.json()]
    inactive_ids = [r["id"] for r in inactive_resp.json()]

    assert r1["id"] not in active_ids
    assert r1["id"] in inactive_ids


# ── GET /routes/{id} tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_route_by_id(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)

    create_resp = await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)
    route_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/routes/{route_id}", headers=headers)
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["id"] == route_id
    assert "route_segments" in data
    assert data["route_segments"] == []


@pytest.mark.asyncio
async def test_get_route_not_found(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    response = await client.get(
        f"/api/v1/routes/{uuid.uuid4()}",
        headers=make_auth_headers(token),
    )
    assert response.status_code == 404
    body = response.json()
    assert "error_code" in body
    assert body["error_code"] == "ROUTE_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_route_soft_deleted_returns_404(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]
    await client.delete(f"/api/v1/routes/{route_id}", headers=headers)

    get_resp = await client.get(f"/api/v1/routes/{route_id}", headers=headers)
    assert get_resp.status_code == 404


# ── GET /routes/{id}/traffic tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_route_traffic_empty(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]

    resp = await client.get(f"/api/v1/routes/{route_id}/traffic", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["route_id"] == route_id
    assert data["worst_congestion_level"] is None
    assert data["segment_count"] == 0


@pytest.mark.asyncio
async def test_get_route_traffic_not_found(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    resp = await client.get(
        f"/api/v1/routes/{uuid.uuid4()}/traffic",
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 404


# ── PUT /routes/{id} tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_route(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]

    resp = await client.put(
        f"/api/v1/routes/{route_id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_route_not_found(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    # Use a 2+ char name so Pydantic validation passes; the 404 comes from the service.
    resp = await client.put(
        f"/api/v1/routes/{uuid.uuid4()}",
        json={"name": "XX"},
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_user_cannot_update_route(
    client: AsyncClient, admin_user, public_user
) -> None:
    admin_token = await login_user(client, admin_user.email, "AdminPass1")
    route_id = (
        await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=make_auth_headers(admin_token))
    ).json()["id"]

    pub_token = await login_user(client, public_user.email, "TestPass1")
    resp = await client.put(
        f"/api/v1/routes/{route_id}",
        json={"name": "X"},
        headers=make_auth_headers(pub_token),
    )
    assert resp.status_code == 403


# ── POST /routes/{id}/segments tests ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_segment_to_route(client: AsyncClient, admin_user, test_db: AsyncSession) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]
    seg = await _create_segment(test_db)

    resp = await client.post(
        f"/api/v1/routes/{route_id}/segments",
        json={"segment_id": str(seg.id), "sequence_order": 1},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["segment_id"] == str(seg.id)
    assert data["sequence_order"] == 1


@pytest.mark.asyncio
async def test_add_segment_sequence_conflict(
    client: AsyncClient, admin_user, test_db: AsyncSession
) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]
    seg1 = await _create_segment(test_db)
    seg2 = await _create_segment(test_db)

    await client.post(
        f"/api/v1/routes/{route_id}/segments",
        json={"segment_id": str(seg1.id), "sequence_order": 1},
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/routes/{route_id}/segments",
        json={"segment_id": str(seg2.id), "sequence_order": 1},
        headers=headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "ROUTE_SEQUENCE_CONFLICT"


@pytest.mark.asyncio
async def test_add_segment_route_not_found(client: AsyncClient, admin_user, test_db: AsyncSession) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    seg = await _create_segment(test_db)
    resp = await client.post(
        f"/api/v1/routes/{uuid.uuid4()}/segments",
        json={"segment_id": str(seg.id), "sequence_order": 1},
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_user_cannot_add_segment(
    client: AsyncClient, admin_user, public_user, test_db: AsyncSession
) -> None:
    admin_token = await login_user(client, admin_user.email, "AdminPass1")
    route_id = (
        await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=make_auth_headers(admin_token))
    ).json()["id"]
    seg = await _create_segment(test_db)

    pub_token = await login_user(client, public_user.email, "TestPass1")
    resp = await client.post(
        f"/api/v1/routes/{route_id}/segments",
        json={"segment_id": str(seg.id), "sequence_order": 1},
        headers=make_auth_headers(pub_token),
    )
    assert resp.status_code == 403


# ── DELETE /routes/{id}/segments/{sid} tests ─────────────────────────────────

@pytest.mark.asyncio
async def test_remove_segment_from_route(
    client: AsyncClient, admin_user, test_db: AsyncSession
) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]
    seg = await _create_segment(test_db)

    await client.post(
        f"/api/v1/routes/{route_id}/segments",
        json={"segment_id": str(seg.id), "sequence_order": 1},
        headers=headers,
    )
    resp = await client.delete(f"/api/v1/routes/{route_id}/segments/{seg.id}", headers=headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_remove_segment_not_in_route(
    client: AsyncClient, admin_user, test_db: AsyncSession
) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]
    seg = await _create_segment(test_db)

    resp = await client.delete(f"/api/v1/routes/{route_id}/segments/{seg.id}", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "SEGMENT_NOT_IN_ROUTE"


# ── DELETE /routes/{id} tests ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_route(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]

    resp = await client.delete(f"/api/v1/routes/{route_id}", headers=headers)
    assert resp.status_code == 204

    get_resp = await client.get(f"/api/v1/routes/{route_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_route_not_found(client: AsyncClient, admin_user) -> None:
    token = await login_user(client, admin_user.email, "AdminPass1")
    resp = await client.delete(
        f"/api/v1/routes/{uuid.uuid4()}",
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_user_cannot_delete_route(
    client: AsyncClient, admin_user, public_user
) -> None:
    admin_token = await login_user(client, admin_user.email, "AdminPass1")
    route_id = (
        await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=make_auth_headers(admin_token))
    ).json()["id"]

    pub_token = await login_user(client, public_user.email, "TestPass1")
    resp = await client.delete(f"/api/v1/routes/{route_id}", headers=make_auth_headers(pub_token))
    assert resp.status_code == 403


# ── Validation tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_route_invalid_distance(client: AsyncClient, admin_user) -> None:
    """total_distance_km <= 0 triggers a 422 validation error."""
    token = await login_user(client, admin_user.email, "AdminPass1")
    resp = await client.post(
        "/api/v1/routes",
        json={**ROUTE_PAYLOAD, "total_distance_km": -5.0},
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_route_missing_fields(client: AsyncClient, admin_user) -> None:
    """Missing required fields return 422."""
    token = await login_user(client, admin_user.email, "AdminPass1")
    resp = await client.post(
        "/api/v1/routes",
        json={"name": "Partial"},
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_add_segment_zero_sequence_order(
    client: AsyncClient, admin_user, test_db: AsyncSession
) -> None:
    """sequence_order = 0 violates ge=1 constraint → 422."""
    token = await login_user(client, admin_user.email, "AdminPass1")
    headers = make_auth_headers(token)
    route_id = (await client.post("/api/v1/routes", json=ROUTE_PAYLOAD, headers=headers)).json()["id"]
    seg = await _create_segment(test_db)

    resp = await client.post(
        f"/api/v1/routes/{route_id}/segments",
        json={"segment_id": str(seg.id), "sequence_order": 0},
        headers=headers,
    )
    assert resp.status_code == 422

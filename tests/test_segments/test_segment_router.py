"""
tests/test_segments/test_segment_router.py
"""
import uuid

import pytest
from app.models.user import User
from tests.conftest import login_user, make_auth_headers

from httpx import AsyncClient

from app.models.segment import SegmentStatus
from app.schemas.segment import SegmentCreate


@pytest.fixture
def segment_payload() -> dict:
    return {
        "name": "Test Segment",
        "start_point": "Start",
        "end_point": "End",
        "start_latitude": 28.61,
        "start_longitude": 77.20,
        "end_latitude": 28.65,
        "end_longitude": 77.08,
        "length_km": 5.0,
        "speed_limit_kmh": 60,
        "status": "ACTIVE"
    }


@pytest.mark.asyncio
async def test_create_segment_admin(
    client: AsyncClient, admin_user: User, segment_payload: dict
) -> None:
    token = await login_user(client, "admin@example.com", "AdminPass1")
    response = await client.post(
        "/api/v1/segments",
        json=segment_payload,
        headers=make_auth_headers(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Segment"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_segment_forbidden_for_user(
    client: AsyncClient, public_user: User, segment_payload: dict
) -> None:
    token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.post(
        "/api/v1/segments",
        json=segment_payload,
        headers=make_auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_segment(
    client: AsyncClient, admin_user: User, public_user: User, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    # Create as admin
    post_resp = await client.post(
        "/api/v1/segments",
        json=segment_payload,
        headers=make_auth_headers(admin_token),
    )
    assert post_resp.status_code == 201
    segment_id = post_resp.json()["id"]

    user_token = await login_user(client, "testuser@example.com", "TestPass1")
    # Read as regular user
    get_resp = await client.get(
        f"/api/v1/segments/{segment_id}",
        headers=make_auth_headers(user_token),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == segment_id


@pytest.mark.asyncio
async def test_list_segments(
    client: AsyncClient, admin_user: User, public_user: User, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    await client.post(
        "/api/v1/segments",
        json=segment_payload,
        headers=make_auth_headers(admin_token),
    )
    
    user_token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.get(
        "/api/v1/segments",
        headers=make_auth_headers(user_token),
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_update_segment(
    client: AsyncClient, admin_user: User, segment_payload: dict
) -> None:
    token = await login_user(client, "admin@example.com", "AdminPass1")
    post_resp = await client.post(
        "/api/v1/segments",
        json=segment_payload,
        headers=make_auth_headers(token),
    )
    segment_id = post_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/segments/{segment_id}",
        json={"speed_limit_kmh": 80},
        headers=make_auth_headers(token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["speed_limit_kmh"] == 80


@pytest.mark.asyncio
async def test_delete_segment(
    client: AsyncClient, admin_user: User, segment_payload: dict
) -> None:
    token = await login_user(client, "admin@example.com", "AdminPass1")
    post_resp = await client.post(
        "/api/v1/segments",
        json=segment_payload,
        headers=make_auth_headers(token),
    )
    segment_id = post_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/segments/{segment_id}",
        headers=make_auth_headers(token),
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/segments/{segment_id}",
        headers=make_auth_headers(token),
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_update_segment_forbidden_for_public_user(
    client: AsyncClient, public_user: User, admin_user: User, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    post_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = post_resp.json()["id"]

    user_token = await login_user(client, "testuser@example.com", "TestPass1")
    update_resp = await client.put(f"/api/v1/segments/{segment_id}", json={"speed_limit_kmh": 80}, headers=make_auth_headers(user_token))
    assert update_resp.status_code == 403


@pytest.mark.asyncio
async def test_update_segment_forbidden_for_traffic_controller(
    client: AsyncClient, traffic_controller_user: User, admin_user: User, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    post_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = post_resp.json()["id"]

    controller_token = await login_user(client, "controller@example.com", "ControllerPass1")
    update_resp = await client.put(f"/api/v1/segments/{segment_id}", json={"speed_limit_kmh": 80}, headers=make_auth_headers(controller_token))
    assert update_resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_segment_forbidden_for_public_user(
    client: AsyncClient, public_user: User, admin_user: User, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    post_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = post_resp.json()["id"]

    user_token = await login_user(client, "testuser@example.com", "TestPass1")
    del_resp = await client.delete(f"/api/v1/segments/{segment_id}", headers=make_auth_headers(user_token))
    assert del_resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_segment_forbidden_for_traffic_controller(
    client: AsyncClient, traffic_controller_user: User, admin_user: User, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    post_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = post_resp.json()["id"]

    controller_token = await login_user(client, "controller@example.com", "ControllerPass1")
    del_resp = await client.delete(f"/api/v1/segments/{segment_id}", headers=make_auth_headers(controller_token))
    assert del_resp.status_code == 403

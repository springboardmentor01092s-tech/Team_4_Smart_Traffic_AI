"""
tests/test_alerts/test_alert_router.py
"""
import uuid

import pytest
from httpx import AsyncClient

from app.models.user import User
from tests.conftest import login_user, make_auth_headers


@pytest.fixture
def alert_payload() -> dict:
    return {
        "title": "Severe Congestion",
        "description": "Traffic is completely stopped.",
        "alert_type": "CONGESTION",
        "severity": "CRITICAL"
    }


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
async def test_create_alert_admin(
    client: AsyncClient, admin_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    token = await login_user(client, "admin@example.com", "AdminPass1")
    headers = make_auth_headers(token)
    
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=headers)
    segment_id = seg_resp.json()["id"]
    alert_payload["segment_id"] = segment_id

    response = await client.post("/api/v1/alerts", json=alert_payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Severe Congestion"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_alert_traffic_controller(
    client: AsyncClient, admin_user: User, traffic_controller_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = seg_resp.json()["id"]
    alert_payload["segment_id"] = segment_id

    tc_token = await login_user(client, "controller@example.com", "ControllerPass1")
    response = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(tc_token))
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_alert_forbidden_for_user(
    client: AsyncClient, admin_user: User, public_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = seg_resp.json()["id"]
    alert_payload["segment_id"] = segment_id

    user_token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(user_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_alert(
    client: AsyncClient, admin_user: User, public_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = seg_resp.json()["id"]
    alert_payload["segment_id"] = segment_id

    alert_resp = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))
    alert_id = alert_resp.json()["id"]

    user_token = await login_user(client, "testuser@example.com", "TestPass1")
    get_resp = await client.get(f"/api/v1/alerts/{alert_id}", headers=make_auth_headers(user_token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == alert_id


@pytest.mark.asyncio
async def test_list_alerts(
    client: AsyncClient, admin_user: User, public_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    segment_id = seg_resp.json()["id"]
    alert_payload["segment_id"] = segment_id

    await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))

    user_token = await login_user(client, "testuser@example.com", "TestPass1")
    response = await client.get("/api/v1/alerts", headers=make_auth_headers(user_token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) >= 1


@pytest.mark.asyncio
async def test_update_alert(
    client: AsyncClient, admin_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    alert_payload["segment_id"] = seg_resp.json()["id"]

    alert_resp = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))
    alert_id = alert_resp.json()["id"]

    update_resp = await client.put(
        f"/api/v1/alerts/{alert_id}",
        json={"title": "Updated Title"},
        headers=make_auth_headers(admin_token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_resolve_alert(
    client: AsyncClient, admin_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    alert_payload["segment_id"] = seg_resp.json()["id"]

    alert_resp = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))
    alert_id = alert_resp.json()["id"]

    resolve_resp = await client.patch(
        f"/api/v1/alerts/{alert_id}/resolve",
        headers=make_auth_headers(admin_token),
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["status"] == "RESOLVED"
    assert resolve_resp.json()["resolved_at"] is not None


@pytest.mark.asyncio
async def test_dismiss_alert(
    client: AsyncClient, admin_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    alert_payload["segment_id"] = seg_resp.json()["id"]

    alert_resp = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))
    alert_id = alert_resp.json()["id"]

    dismiss_resp = await client.patch(
        f"/api/v1/alerts/{alert_id}/dismiss",
        headers=make_auth_headers(admin_token),
    )
    assert dismiss_resp.status_code == 200
    assert dismiss_resp.json()["status"] == "DISMISSED"
    assert dismiss_resp.json()["resolved_at"] is not None


@pytest.mark.asyncio
async def test_delete_alert_admin(
    client: AsyncClient, admin_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    alert_payload["segment_id"] = seg_resp.json()["id"]

    alert_resp = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))
    alert_id = alert_resp.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/alerts/{alert_id}",
        headers=make_auth_headers(admin_token),
    )
    assert del_resp.status_code == 204

    get_resp = await client.get(
        f"/api/v1/alerts/{alert_id}",
        headers=make_auth_headers(admin_token),
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_alert_forbidden_for_traffic_controller(
    client: AsyncClient, traffic_controller_user: User, admin_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    alert_payload["segment_id"] = seg_resp.json()["id"]

    alert_resp = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))
    alert_id = alert_resp.json()["id"]

    tc_token = await login_user(client, "controller@example.com", "ControllerPass1")
    del_resp = await client.delete(
        f"/api/v1/alerts/{alert_id}",
        headers=make_auth_headers(tc_token),
    )
    assert del_resp.status_code == 403


@pytest.mark.asyncio
async def test_update_alert_not_active(
    client: AsyncClient, admin_user: User, alert_payload: dict, segment_payload: dict
) -> None:
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    seg_resp = await client.post("/api/v1/segments", json=segment_payload, headers=make_auth_headers(admin_token))
    alert_payload["segment_id"] = seg_resp.json()["id"]

    alert_resp = await client.post("/api/v1/alerts", json=alert_payload, headers=make_auth_headers(admin_token))
    alert_id = alert_resp.json()["id"]

    await client.patch(f"/api/v1/alerts/{alert_id}/resolve", headers=make_auth_headers(admin_token))

    update_resp = await client.put(
        f"/api/v1/alerts/{alert_id}",
        json={"title": "Updated Title"},
        headers=make_auth_headers(admin_token),
    )
    assert update_resp.status_code == 409
    assert "not in active" in update_resp.json()["detail"].lower()

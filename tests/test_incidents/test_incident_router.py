import pytest
from httpx import AsyncClient

from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_report_incident_as_admin(client: AsyncClient, admin_user, segment):
    """Admin can report an incident."""
    response = await client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "AdminPass1"})
    token = response.json()
    headers = make_auth_headers(token["access_token"])

    response = await client.post(
        "/api/v1/incidents",
        headers=headers,
        json={
            "segment_id": str(segment.id),
            "title": "Crash on main highway",
            "description": "Two cars involved",
            "incident_type": "ACCIDENT",
            "severity": "HIGH",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_report_incident_as_public_user(client: AsyncClient, public_user, segment):
    """Public user cannot report incidents."""
    response = await client.post("/api/v1/auth/login", json={"email": public_user.email, "password": "TestPass1"})
    token = response.json()
    headers = make_auth_headers(token["access_token"])

    response = await client.post(
        "/api/v1/incidents",
        headers=headers,
        json={
            "segment_id": str(segment.id),
            "title": "Crash on main highway",
            "description": "Two cars involved",
            "incident_type": "ACCIDENT",
            "severity": "HIGH",
        },
    )
    assert response.status_code == 403

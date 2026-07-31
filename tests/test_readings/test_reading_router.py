import uuid
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from tests.conftest import login_user, make_auth_headers

from app.models.camera import CameraStatus, TrafficCamera
from app.models.segment import CongestionLevel, TrafficSegment, SegmentStatus
from app.repositories.camera_repository import CameraRepository
from app.repositories.segment_repository import SegmentRepository


@pytest.fixture
async def sample_segment(test_db: AsyncSession):
    camera_repo = CameraRepository(test_db)
    camera = await camera_repo.create(
        name="Test Camera", location_name="Test Location", latitude=0.0, longitude=0.0, status=CameraStatus.ACTIVE
    )
    segment_repo = SegmentRepository(test_db)
    segment = await segment_repo.create(
        name="Test Segment",
        start_point="Start",
        end_point="End",
        start_latitude=0.0,
        start_longitude=0.0,
        end_latitude=1.0,
        end_longitude=1.0,
        length_km=10.0,
        speed_limit_kmh=100,
        camera_id=camera.id,
        status=SegmentStatus.ACTIVE,
    )
    return segment


@pytest.mark.asyncio
async def test_submit_reading(client: AsyncClient, admin_user: User, sample_segment: TrafficSegment):
    token = await login_user(client, "admin@example.com", "AdminPass1")
    recorded_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    response = await client.post(
        "/api/v1/readings",
        json={
            "segment_id": str(sample_segment.id),
            "vehicle_count": 50,
            "average_speed_kmh": 60.5,
            "congestion_level": "MODERATE",
            "recorded_at": recorded_at,
        },
        headers=make_auth_headers(token)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["segment_id"] == str(sample_segment.id)
    assert data["vehicle_count"] == 50
    assert data["congestion_level"] == "MODERATE"


@pytest.mark.asyncio
async def test_submit_reading_public_user_forbidden(client: AsyncClient, public_user: User, sample_segment: TrafficSegment):
    token = await login_user(client, "testuser@example.com", "TestPass1")
    recorded_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    response = await client.post(
        "/api/v1/readings",
        json={
            "segment_id": str(sample_segment.id),
            "vehicle_count": 50,
            "average_speed_kmh": 60.5,
            "congestion_level": "MODERATE",
            "recorded_at": recorded_at,
        },
        headers=make_auth_headers(token)
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_reading(client: AsyncClient, admin_user: User, sample_segment: TrafficSegment):
    token = await login_user(client, "admin@example.com", "AdminPass1")
    recorded_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    create_response = await client.post(
        "/api/v1/readings",
        json={
            "segment_id": str(sample_segment.id),
            "vehicle_count": 50,
            "average_speed_kmh": 60.5,
            "congestion_level": "MODERATE",
            "recorded_at": recorded_at,
        },
        headers=make_auth_headers(token)
    )
    reading_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/readings/{reading_id}",
        headers=make_auth_headers(token)
    )
    assert response.status_code == 200
    assert response.json()["id"] == reading_id


@pytest.mark.asyncio
async def test_list_readings(client: AsyncClient, admin_user: User, sample_segment: TrafficSegment):
    token = await login_user(client, "admin@example.com", "AdminPass1")
    recorded_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    await client.post(
        "/api/v1/readings",
        json={
            "segment_id": str(sample_segment.id),
            "vehicle_count": 50,
            "average_speed_kmh": 60.5,
            "congestion_level": "MODERATE",
            "recorded_at": recorded_at,
        },
        headers=make_auth_headers(token)
    )

    response = await client.get(
        f"/api/v1/readings?segment_id={sample_segment.id}",
        headers=make_auth_headers(token)
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

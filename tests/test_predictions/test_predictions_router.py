import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.models.prediction import PredictionStatus
from app.models.segment import CongestionLevel

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def sample_prediction(test_db, segment):
    from app.repositories.prediction_repository import PredictionRepository
    repo = PredictionRepository(test_db)
    
    pred = await repo.create(
        segment_id=segment.id,
        prediction_for=datetime.now(UTC) + timedelta(hours=1),
        horizon_minutes=60,
    )
    return pred


async def test_list_predictions(client: AsyncClient, public_user, sample_prediction):
    # Authenticate as PUBLIC_USER
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, public_user.email, "TestPass1")
    
    resp = await client.get("/api/v1/predictions/", headers=make_auth_headers(token))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["id"] == str(sample_prediction.id)


async def test_create_prediction_unauthorized(client: AsyncClient, public_user, segment):
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, public_user.email, "TestPass1")
    
    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    
    resp = await client.post(
        "/api/v1/predictions/",
        json={"segment_id": str(segment.id), "prediction_for": future_time, "horizon_minutes": 60},
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 403


async def test_create_prediction_admin(client: AsyncClient, admin_user, segment):
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, admin_user.email, "AdminPass1")
    
    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    
    resp = await client.post(
        "/api/v1/predictions/",
        json={"segment_id": str(segment.id), "prediction_for": future_time, "horizon_minutes": 60},
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["segment_id"] == str(segment.id)


async def test_complete_prediction(client: AsyncClient, traffic_controller_user, sample_prediction):
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, traffic_controller_user.email, "ControllerPass1")
    
    resp = await client.patch(
        f"/api/v1/predictions/{sample_prediction.id}/complete",
        json={"predicted_congestion_level": "HEAVY", "confidence_score": 0.9},
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert data["predicted_congestion_level"] == "HEAVY"
    assert data["confidence_score"] == 0.9


async def test_delete_prediction_admin(client: AsyncClient, admin_user, sample_prediction):
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, admin_user.email, "AdminPass1")
    
    resp = await client.delete(
        f"/api/v1/predictions/{sample_prediction.id}",
        headers=make_auth_headers(token),
    )
    assert resp.status_code == 204


async def test_get_prediction_soft_deleted_returns_404(client: AsyncClient, admin_user, sample_prediction):
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, admin_user.email, "AdminPass1")
    
    # Delete it first
    del_resp = await client.delete(
        f"/api/v1/predictions/{sample_prediction.id}",
        headers=make_auth_headers(token),
    )
    assert del_resp.status_code == 204
    
    # GET should return 404
    get_resp = await client.get(
        f"/api/v1/predictions/{sample_prediction.id}",
        headers=make_auth_headers(token),
    )
    assert get_resp.status_code == 404
    assert get_resp.json()["error_code"] == "PREDICTION_NOT_FOUND"


async def test_lifecycle_create_complete(client: AsyncClient, traffic_controller_user, segment):
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, traffic_controller_user.email, "ControllerPass1")
    
    # 1. Create
    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/predictions/",
        json={"segment_id": str(segment.id), "prediction_for": future_time, "horizon_minutes": 60},
        headers=make_auth_headers(token),
    )
    assert create_resp.status_code == 201
    pred_data = create_resp.json()
    assert pred_data["status"] == "PENDING"
    assert pred_data["completed_at"] is None
    pred_id = pred_data["id"]
    
    # 2. Complete
    complete_resp = await client.patch(
        f"/api/v1/predictions/{pred_id}/complete",
        json={"predicted_congestion_level": "HEAVY", "confidence_score": 0.95},
        headers=make_auth_headers(token),
    )
    assert complete_resp.status_code == 200
    comp_data = complete_resp.json()
    assert comp_data["status"] == "COMPLETED"
    assert comp_data["completed_at"] is not None
    assert comp_data["requested_at"] == pred_data["requested_at"]


async def test_lifecycle_create_fail(client: AsyncClient, admin_user, segment):
    from tests.conftest import login_user, make_auth_headers
    token = await login_user(client, admin_user.email, "AdminPass1")
    
    # 1. Create
    future_time = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    create_resp = await client.post(
        "/api/v1/predictions/",
        json={"segment_id": str(segment.id), "prediction_for": future_time, "horizon_minutes": 60},
        headers=make_auth_headers(token),
    )
    assert create_resp.status_code == 201
    pred_data = create_resp.json()
    pred_id = pred_data["id"]
    
    # 2. Fail
    fail_resp = await client.patch(
        f"/api/v1/predictions/{pred_id}/fail",
        headers=make_auth_headers(token),
    )
    assert fail_resp.status_code == 200
    fail_data = fail_resp.json()
    assert fail_data["status"] == "FAILED"
    assert fail_data["completed_at"] is not None

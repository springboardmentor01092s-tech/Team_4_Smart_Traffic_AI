import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.segment import TrafficSegment, CongestionLevel
from app.models.alert import Alert, AlertSeverity, AlertStatus
from app.models.notification import Notification, NotificationStatus
from app.models.user import UserRole
from tests.conftest import login_user

@pytest.mark.asyncio
async def test_m3_core_e2e_workflow(
    client: AsyncClient,
    test_db: AsyncSession,
    traffic_controller_user,
    admin_user,
    segment: TrafficSegment,
    monkeypatch
):
    """
    1. Authenticated traffic controller posts a HEAVY reading
    2. Automated HIGH alert is generated
    3. Notification is assigned to admin (and traffic controller)
    4. Heatmap is updated
    5. Trend endpoint remains functional
    6. Insight reflects state
    7. AI report remains valid
    """
    tc_token = await login_user(client, "controller@example.com", "ControllerPass1")
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    
    segment_id = str(segment.id)
    start_lat = segment.start_latitude
    start_lon = segment.start_longitude
    end_lat = segment.end_latitude
    end_lon = segment.end_longitude
    
    # SQLite does not support Postgres date_trunc. Mock it for the E2E test.
    from app.repositories.reading_repository import ReadingRepository
    async def mock_get_hourly_averages(*args, **kwargs):
        return []
    monkeypatch.setattr(ReadingRepository, "get_hourly_averages", mock_get_hourly_averages)
    
    # 1. Submit Reading
    reading_payload = {
        "segment_id": segment_id,
        "vehicle_count": 500,
        "average_speed_kmh": 20,
        "congestion_level": "HEAVY",
        "recorded_at": "2026-01-01T10:00:00Z"
    }
    resp = await client.post(
        "/api/v1/readings",
        json=reading_payload,
        headers={"Authorization": f"Bearer {tc_token}"}
    )
    assert resp.status_code == 201
    
    # 2 & 3. Verify Active Alert and Notification created (synchronous)
    alerts_result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = alerts_result.scalars().all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.status == AlertStatus.ACTIVE
    assert alert.severity == AlertSeverity.HIGH
    
    notifications_result = await test_db.execute(select(Notification).where(Notification.alert_id == alert.id))
    notifications = notifications_result.scalars().all()
    assert len(notifications) > 0
    # Ensure it's assigned to admin/controller role users
    recipients = {n.recipient_user_id for n in notifications}
    assert admin_user.id in recipients
    assert traffic_controller_user.id in recipients
    
    # 4. Verify Heatmap
    resp = await client.get("/api/v1/analytics/congestion-heatmap")
    assert resp.status_code == 200
    heatmap_data = resp.json()
    assert len(heatmap_data) >= 1
    seg_heatmap = next(h for h in heatmap_data if h["segment_id"] == segment_id)
    assert seg_heatmap["congestion_level"] == "HEAVY"
    assert seg_heatmap["start_latitude"] == start_lat
    assert seg_heatmap["start_longitude"] == start_lon
    assert seg_heatmap["end_latitude"] == end_lat
    assert seg_heatmap["end_longitude"] == end_lon

    # 5. Trend endpoint
    resp = await client.get(
        f"/api/v1/analytics/segments/{segment_id}/trends",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    trend_data = resp.json()
    assert "hourly_trends" in trend_data
    
    # 6. Segment insight
    resp = await client.get(
        f"/api/v1/insights/segment/{segment_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    insight_data = resp.json()
    assert insight_data["segment_id"] == segment_id
    assert insight_data["risk_level"] in ["HIGH", "CRITICAL"] # Expecting high because of HIGH alert
    
    # 7. AI Report
    resp = await client.get(
        "/api/v1/analytics/ai-report",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    ai_report = resp.json()
    assert ai_report["active_segment_count"] >= 1
    assert segment_id in [i["segment_id"] for i in ai_report["insights"]]


@pytest.mark.asyncio
async def test_standstill_escalation(
    client: AsyncClient,
    test_db: AsyncSession,
    traffic_controller_user,
    segment: TrafficSegment
):
    tc_token = await login_user(client, "controller@example.com", "ControllerPass1")
    
    # Heavy reading -> HIGH alert
    await client.post(
        "/api/v1/readings",
        json={
            "segment_id": str(segment.id),
            "vehicle_count": 500,
            "average_speed_kmh": 20,
            "congestion_level": "HEAVY",
            "recorded_at": "2026-01-01T10:00:00Z"
        },
        headers={"Authorization": f"Bearer {tc_token}"}
    )
    
    alerts_result = await test_db.execute(
        select(Alert).where(Alert.segment_id == segment.id, Alert.status == AlertStatus.ACTIVE)
    )
    assert len(alerts_result.scalars().all()) == 1
    
    # Standstill reading -> Escalate to CRITICAL
    await client.post(
        "/api/v1/readings",
        json={
            "segment_id": str(segment.id),
            "vehicle_count": 800,
            "average_speed_kmh": 5,
            "congestion_level": "STANDSTILL",
            "recorded_at": "2026-01-01T10:15:00Z"
        },
        headers={"Authorization": f"Bearer {tc_token}"}
    )
    
    alerts_result2 = await test_db.execute(
        select(Alert).where(Alert.segment_id == segment.id, Alert.status == AlertStatus.ACTIVE)
    )
    alerts2 = alerts_result2.scalars().all()
    assert len(alerts2) == 1 # Duplicate suppressed!
    assert alerts2[0].severity == AlertSeverity.CRITICAL


@pytest.mark.asyncio
async def test_incident_workflow(
    client: AsyncClient,
    test_db: AsyncSession,
    traffic_controller_user,
    segment: TrafficSegment
):
    tc_token = await login_user(client, "controller@example.com", "ControllerPass1")
    
    incident_payload = {
        "segment_id": str(segment.id),
        "title": "Crash on main highway",
        "incident_type": "ACCIDENT",
        "severity": "CRITICAL",
        "description": "Multi-car collision"
    }
    resp = await client.post(
        "/api/v1/incidents",
        json=incident_payload,
        headers={"Authorization": f"Bearer {tc_token}"}
    )
    assert resp.status_code == 201
    
    alerts_result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = alerts_result.scalars().all()
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.CRITICAL
    
    # Repeat incident should suppress duplicate alert
    resp2 = await client.post(
        "/api/v1/incidents",
        json=incident_payload,
        headers={"Authorization": f"Bearer {tc_token}"}
    )
    assert resp2.status_code == 201
    
    alerts_result2 = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    assert len(alerts_result2.scalars().all()) == 1


@pytest.mark.asyncio
async def test_notification_security(
    client: AsyncClient,
    test_db: AsyncSession,
    admin_user,
    traffic_controller_user,
    public_user,
    segment: TrafficSegment
):
    # Post reading to trigger notifications
    tc_token = await login_user(client, "controller@example.com", "ControllerPass1")
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    public_token = await login_user(client, "testuser@example.com", "TestPass1")
    
    await client.post(
        "/api/v1/readings",
        json={
            "segment_id": str(segment.id),
            "vehicle_count": 800,
            "average_speed_kmh": 5,
            "congestion_level": "STANDSTILL",
            "recorded_at": "2026-01-01T10:00:00Z"
        },
        headers={"Authorization": f"Bearer {tc_token}"}
    )
    
    # TC fetches their notifications
    tc_resp = await client.get("/api/v1/notifications/me", headers={"Authorization": f"Bearer {tc_token}"})
    assert tc_resp.status_code == 200
    tc_notifs = tc_resp.json()
    assert len(tc_notifs) > 0
    tc_notif_id = tc_notifs[0]["id"]
    
    # Admin tries to mark TC's notification as read
    admin_patch_resp = await client.patch(
        f"/api/v1/notifications/{tc_notif_id}/read",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_patch_resp.status_code == 403
    
    # TC marks own notification as read
    tc_patch_resp = await client.patch(
        f"/api/v1/notifications/{tc_notif_id}/read",
        headers={"Authorization": f"Bearer {tc_token}"}
    )
    assert tc_patch_resp.status_code == 200
    
    # Public user tries to get notifications (they have none)
    public_resp = await client.get("/api/v1/notifications/me", headers={"Authorization": f"Bearer {public_token}"})
    assert public_resp.status_code == 200
    assert public_resp.json() == []


@pytest.mark.asyncio
async def test_report_period_integration(
    client: AsyncClient,
    admin_user,
    segment: TrafficSegment,
    monkeypatch
):
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    
    # Mock date_trunc for SQLite
    from app.repositories.reading_repository import ReadingRepository
    async def mock_get_hourly_averages(*args, **kwargs):
        return []
    monkeypatch.setattr(ReadingRepository, "get_hourly_averages", mock_get_hourly_averages)
    
    # Explicit period
    resp_explicit = await client.get(
        "/api/v1/analytics/ai-report?from_dt=2026-01-01T00:00:00Z&to_dt=2026-01-02T00:00:00Z",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_explicit.status_code == 200
    
    # Invalid period
    resp_invalid = await client.get(
        "/api/v1/analytics/ai-report?from_dt=2026-01-02T00:00:00Z&to_dt=2026-01-01T00:00:00Z",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_invalid.status_code == 422

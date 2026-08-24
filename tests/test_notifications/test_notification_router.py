import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationStatus
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_get_my_notifications(client: AsyncClient, admin_user, test_db: AsyncSession, segment):
    """Test getting notifications for the current user."""
    # First, let's create a notification
    from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
    alert = Alert(
        segment_id=segment.id,
        title="Test Alert",
        description="Test description",
        alert_type=AlertType.CONGESTION,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.ACTIVE,
    )
    test_db.add(alert)
    await test_db.flush()
    
    notification = Notification(
        recipient_user_id=admin_user.id,
        alert_id=alert.id,
        title="Test Notification",
        message="Test msg",
        status=NotificationStatus.PENDING,
    )
    test_db.add(notification)
    await test_db.commit()
    await test_db.refresh(notification)

    response = await client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "AdminPass1"})
    token = response.json()
    headers = make_auth_headers(token["access_token"])

    response = await client.get("/api/v1/notifications/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Notification"
    assert data[0]["read_at"] is None


@pytest.mark.asyncio
async def test_mark_notification_read(client: AsyncClient, admin_user, test_db: AsyncSession, segment):
    """Test marking a notification as read."""
    # First, let's create a notification
    from app.models.alert import Alert, AlertType, AlertSeverity, AlertStatus
    alert = Alert(
        segment_id=segment.id,
        title="Test Alert",
        description="Test description",
        alert_type=AlertType.CONGESTION,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.ACTIVE,
    )
    test_db.add(alert)
    await test_db.flush()
    
    notification = Notification(
        recipient_user_id=admin_user.id,
        alert_id=alert.id,
        title="Test Notification",
        message="Test msg",
        status=NotificationStatus.PENDING,
    )
    test_db.add(notification)
    await test_db.commit()
    await test_db.refresh(notification)

    response = await client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "AdminPass1"})
    token = response.json()
    headers = make_auth_headers(token["access_token"])

    response = await client.patch(f"/api/v1/notifications/{notification.id}/read", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["read_at"] is not None

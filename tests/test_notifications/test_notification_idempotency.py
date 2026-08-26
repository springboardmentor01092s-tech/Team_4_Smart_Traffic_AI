"""
tests/test_notifications/test_notification_idempotency.py

Tests for notification deduplication, uniqueness constraint, and idempotency.
"""
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.notification import Notification, NotificationStatus
from app.models.segment import TrafficSegment
from app.models.user import User, UserRole
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_provider import LogNotificationProvider
from app.services.notification_service import NotificationService


@pytest.mark.asyncio
async def test_notification_uniqueness_db_constraint(test_db: AsyncSession, admin_user: User) -> None:
    """Verify that inserting duplicate (recipient_user_id, alert_id) violates unique constraint."""
    # Create segment & alert
    seg = TrafficSegment(
        name="Alert Seg", start_point="A", end_point="B",
        start_latitude=40.0, start_longitude=-74.0,
        end_latitude=40.1, end_longitude=-74.1,
        length_km=5.0, speed_limit_kmh=60
    )
    test_db.add(seg)
    await test_db.flush()

    alert = Alert(
        segment_id=seg.id,
        title="Test Alert",
        alert_type=AlertType.CONGESTION,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.ACTIVE,
    )
    test_db.add(alert)
    await test_db.commit()

    repo = NotificationRepository(test_db)
    # 1. Create first notification -> Success
    n1 = await repo.create(
        recipient_user_id=admin_user.id,
        alert_id=alert.id,
        title="Alert Title",
        message="Alert Message",
    )
    assert n1.id is not None

    # 2. Attempt duplicate create -> IntegrityError
    with pytest.raises(IntegrityError):
        n2 = Notification(
            recipient_user_id=admin_user.id,
            alert_id=alert.id,
            title="Duplicate Title",
            message="Duplicate Message",
        )
        test_db.add(n2)
        await test_db.flush()
    await test_db.rollback()


@pytest.mark.asyncio
async def test_notification_service_idempotent_generation(test_db: AsyncSession, admin_user: User) -> None:
    """Verify NotificationService.generate_notifications_for_alert is fully idempotent."""
    seg = TrafficSegment(
        name="Alert Seg 2", start_point="A", end_point="B",
        start_latitude=40.0, start_longitude=-74.0,
        end_latitude=40.1, end_longitude=-74.1,
        length_km=5.0, speed_limit_kmh=60
    )
    test_db.add(seg)
    await test_db.flush()

    alert = Alert(
        segment_id=seg.id,
        title="Accident Ahead",
        alert_type=AlertType.ACCIDENT,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.ACTIVE,
    )
    test_db.add(alert)
    await test_db.commit()

    notification_repo = NotificationRepository(test_db)
    user_repo = UserRepository(test_db)
    provider = LogNotificationProvider()
    service = NotificationService(notification_repo, user_repo, provider)

    # First generation
    generated_first = await service.generate_notifications_for_alert(alert)
    assert len(generated_first) >= 1

    # Second generation for the same alert -> returns 0 new notifications (deduplicated)
    generated_second = await service.generate_notifications_for_alert(alert)
    assert len(generated_second) == 0

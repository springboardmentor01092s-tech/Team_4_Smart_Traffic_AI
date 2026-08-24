import pytest
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.reading import TrafficReading
from app.models.segment import CongestionLevel, TrafficSegment
from app.repositories.alert_repository import AlertRepository
from app.repositories.segment_repository import SegmentRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository
from app.services.alert_service import AlertService
from app.services.alert_evaluator import AlertEvaluatorService
from app.services.notification_service import NotificationService
from app.services.notification_provider import LogNotificationProvider

pytestmark = pytest.mark.asyncio


@pytest.fixture
def alert_service(test_db: AsyncSession) -> AlertService:
    return AlertService(AlertRepository(test_db), SegmentRepository(test_db))

@pytest.fixture
def notification_service(test_db: AsyncSession) -> NotificationService:
    return NotificationService(
        NotificationRepository(test_db),
        UserRepository(test_db),
        LogNotificationProvider()
    )


@pytest.fixture
def alert_evaluator(alert_service: AlertService, notification_service: NotificationService) -> AlertEvaluatorService:
    return AlertEvaluatorService(alert_service, notification_service)


async def create_reading(test_db: AsyncSession, segment: TrafficSegment, congestion: CongestionLevel) -> TrafficReading:
    reading = TrafficReading(
        segment_id=segment.id,
        vehicle_count=100,
        average_speed_kmh=10.0,
        congestion_level=congestion,
        recorded_at=datetime.now(UTC),
    )
    test_db.add(reading)
    await test_db.flush()
    return reading


async def test_heavy_reading_creates_high_alert(
    test_db: AsyncSession,
    segment: TrafficSegment,
    alert_evaluator: AlertEvaluatorService,
):
    reading = await create_reading(test_db, segment, CongestionLevel.HEAVY)
    await alert_evaluator.evaluate_reading(reading)

    result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = result.scalars().all()
    
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH
    assert alerts[0].status == AlertStatus.ACTIVE
    assert alerts[0].alert_type == AlertType.CONGESTION


async def test_standstill_reading_creates_critical_alert(
    test_db: AsyncSession,
    segment: TrafficSegment,
    alert_evaluator: AlertEvaluatorService,
):
    reading = await create_reading(test_db, segment, CongestionLevel.STANDSTILL)
    await alert_evaluator.evaluate_reading(reading)

    result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = result.scalars().all()
    
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.CRITICAL


async def test_non_triggering_reading_creates_no_alert(
    test_db: AsyncSession,
    segment: TrafficSegment,
    alert_evaluator: AlertEvaluatorService,
):
    reading = await create_reading(test_db, segment, CongestionLevel.MODERATE)
    await alert_evaluator.evaluate_reading(reading)

    result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = result.scalars().all()
    
    assert len(alerts) == 0


async def test_repeated_heavy_readings_do_not_create_duplicate_alerts(
    test_db: AsyncSession,
    segment: TrafficSegment,
    alert_evaluator: AlertEvaluatorService,
):
    reading1 = await create_reading(test_db, segment, CongestionLevel.HEAVY)
    await alert_evaluator.evaluate_reading(reading1)
    
    reading2 = await create_reading(test_db, segment, CongestionLevel.HEAVY)
    await alert_evaluator.evaluate_reading(reading2)

    result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = result.scalars().all()
    
    # Should still only be 1 alert
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH


async def test_heavy_to_standstill_escalates_existing_alert(
    test_db: AsyncSession,
    segment: TrafficSegment,
    alert_evaluator: AlertEvaluatorService,
):
    reading1 = await create_reading(test_db, segment, CongestionLevel.HEAVY)
    await alert_evaluator.evaluate_reading(reading1)

    result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = result.scalars().all()
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.HIGH
    
    reading2 = await create_reading(test_db, segment, CongestionLevel.STANDSTILL)
    await alert_evaluator.evaluate_reading(reading2)

    result2 = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts2 = result2.scalars().all()
    
    assert len(alerts2) == 1
    assert alerts2[0].severity == AlertSeverity.CRITICAL


async def test_repeated_standstill_does_not_create_duplicate_alerts(
    test_db: AsyncSession,
    segment: TrafficSegment,
    alert_evaluator: AlertEvaluatorService,
):
    reading1 = await create_reading(test_db, segment, CongestionLevel.STANDSTILL)
    await alert_evaluator.evaluate_reading(reading1)
    
    reading2 = await create_reading(test_db, segment, CongestionLevel.STANDSTILL)
    await alert_evaluator.evaluate_reading(reading2)

    result = await test_db.execute(select(Alert).where(Alert.segment_id == segment.id))
    alerts = result.scalars().all()
    
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.CRITICAL

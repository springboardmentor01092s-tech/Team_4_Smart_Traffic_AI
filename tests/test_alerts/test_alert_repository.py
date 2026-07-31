"""
tests/test_alerts/test_alert_repository.py
"""
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.segment import SegmentStatus, TrafficSegment
from app.repositories.alert_repository import AlertRepository
from app.repositories.segment_repository import SegmentRepository


async def make_segment(repo: SegmentRepository) -> TrafficSegment:
    return await repo.create(
        name="Test Segment",
        start_point="Start",
        end_point="End",
        start_latitude=28.61,
        start_longitude=77.20,
        end_latitude=28.65,
        end_longitude=77.08,
        length_km=5.0,
        speed_limit_kmh=60,
    )


async def make_alert(
    repo: AlertRepository,
    segment_id: uuid.UUID,
    *,
    title: str = "Test Alert",
    description: str = "Test Description",
    alert_type: AlertType = AlertType.CONGESTION,
    severity: AlertSeverity = AlertSeverity.HIGH,
    status: AlertStatus = AlertStatus.ACTIVE,
    created_by: uuid.UUID | None = None,
) -> Alert:
    return await repo.create(
        segment_id=segment_id,
        created_by=created_by,
        title=title,
        description=description,
        alert_type=alert_type,
        severity=severity,
        status=status,
    )


@pytest.mark.asyncio
async def test_create_alert(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    alert = await make_alert(repo, segment_id=segment.id, title="Test Alert A")
    
    assert alert.id is not None
    assert alert.title == "Test Alert A"
    assert alert.status == AlertStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_by_id(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    alert = await make_alert(repo, segment_id=segment.id)
    
    fetched = await repo.get_by_id(alert.id)
    assert fetched is not None
    assert fetched.id == alert.id


@pytest.mark.asyncio
async def test_get_by_id_soft_deleted(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    alert = await make_alert(repo, segment_id=segment.id)
    await repo.soft_delete(alert)
    
    fetched = await repo.get_by_id(alert.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_get_all(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    alert1 = await make_alert(repo, segment_id=segment.id, title="Alert 1")
    alert2 = await make_alert(repo, segment_id=segment.id, title="Alert 2")
    
    alerts = await repo.get_all()
    ids = {a.id for a in alerts}
    assert alert1.id in ids
    assert alert2.id in ids


@pytest.mark.asyncio
async def test_get_all_excludes_soft_deleted(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    active_alert = await make_alert(repo, segment_id=segment.id, title="Active")
    deleted_alert = await make_alert(repo, segment_id=segment.id, title="Deleted")
    await repo.soft_delete(deleted_alert)
    
    alerts = await repo.get_all()
    ids = {a.id for a in alerts}
    assert active_alert.id in ids
    assert deleted_alert.id not in ids


@pytest.mark.asyncio
async def test_update_alert(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    alert = await make_alert(repo, segment_id=segment.id, title="Old Title")
    
    updated = await repo.update(alert, title="New Title")
    assert updated.title == "New Title"


@pytest.mark.asyncio
async def test_soft_delete(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    alert = await make_alert(repo, segment_id=segment.id)
    assert alert.deleted_at is None
    
    await repo.soft_delete(alert)
    assert alert.deleted_at is not None


@pytest.mark.asyncio
async def test_get_all_filters_by_segment_id(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment1 = await make_segment(seg_repo)
    segment2 = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    alert1 = await make_alert(repo, segment_id=segment1.id, title="Alert on Seg 1")
    alert2 = await make_alert(repo, segment_id=segment2.id, title="Alert on Seg 2")
    
    alerts = await repo.get_all(segment_id=segment1.id)
    ids = {a.id for a in alerts}
    assert alert1.id in ids
    assert alert2.id not in ids


@pytest.mark.asyncio
async def test_get_all_filters_by_status(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    active_alert = await make_alert(repo, segment_id=segment.id, status=AlertStatus.ACTIVE)
    resolved_alert = await make_alert(repo, segment_id=segment.id, status=AlertStatus.RESOLVED)
    
    alerts = await repo.get_all(status=AlertStatus.RESOLVED)
    ids = {a.id for a in alerts}
    assert resolved_alert.id in ids
    assert active_alert.id not in ids


@pytest.mark.asyncio
async def test_get_all_filters_by_severity(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    high_alert = await make_alert(repo, segment_id=segment.id, severity=AlertSeverity.HIGH)
    critical_alert = await make_alert(repo, segment_id=segment.id, severity=AlertSeverity.CRITICAL)
    
    alerts = await repo.get_all(severity=AlertSeverity.CRITICAL)
    ids = {a.id for a in alerts}
    assert critical_alert.id in ids
    assert high_alert.id not in ids


@pytest.mark.asyncio
async def test_get_all_filters_by_alert_type(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    acc_alert = await make_alert(repo, segment_id=segment.id, alert_type=AlertType.ACCIDENT)
    wea_alert = await make_alert(repo, segment_id=segment.id, alert_type=AlertType.WEATHER)
    
    alerts = await repo.get_all(alert_type=AlertType.WEATHER)
    ids = {a.id for a in alerts}
    assert wea_alert.id in ids
    assert acc_alert.id not in ids


@pytest.mark.asyncio
async def test_get_active_count(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    initial_count = await repo.get_active_count()

    active1 = await make_alert(repo, segment_id=segment.id, status=AlertStatus.ACTIVE)
    active2 = await make_alert(repo, segment_id=segment.id, status=AlertStatus.ACTIVE)
    resolved = await make_alert(repo, segment_id=segment.id, status=AlertStatus.RESOLVED)
    deleted = await make_alert(repo, segment_id=segment.id, status=AlertStatus.ACTIVE)
    await repo.soft_delete(deleted)
    
    count = await repo.get_active_count()
    assert count == initial_count + 2


@pytest.mark.asyncio
async def test_get_active_by_severity(test_db: AsyncSession) -> None:
    seg_repo = SegmentRepository(test_db)
    segment = await make_segment(seg_repo)

    repo = AlertRepository(test_db)
    initial_count = await repo.get_active_by_severity(AlertSeverity.CRITICAL)

    active_crit = await make_alert(repo, segment_id=segment.id, status=AlertStatus.ACTIVE, severity=AlertSeverity.CRITICAL)
    active_high = await make_alert(repo, segment_id=segment.id, status=AlertStatus.ACTIVE, severity=AlertSeverity.HIGH)
    resolved_crit = await make_alert(repo, segment_id=segment.id, status=AlertStatus.RESOLVED, severity=AlertSeverity.CRITICAL)
    
    count = await repo.get_active_by_severity(AlertSeverity.CRITICAL)
    assert count == initial_count + 1

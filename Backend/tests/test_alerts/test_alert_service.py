"""
tests/test_alerts/test_alert_service.py
"""
import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import AlertNotActiveError, AlertNotFoundError, SegmentNotFoundError
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.segment import TrafficSegment
from app.schemas.alert import AlertCreate, AlertUpdate
from app.services.alert_service import AlertService


@pytest.fixture
def mock_segment_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_alert_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def alert_service(mock_alert_repo: AsyncMock, mock_segment_repo: AsyncMock) -> AlertService:
    return AlertService(alert_repo=mock_alert_repo, segment_repo=mock_segment_repo)


def dummy_segment() -> TrafficSegment:
    return TrafficSegment(id=uuid.uuid4(), name="Test Seg")


def dummy_alert(status: AlertStatus = AlertStatus.ACTIVE) -> Alert:
    return Alert(
        id=uuid.uuid4(),
        segment_id=uuid.uuid4(),
        title="Test Alert",
        status=status,
    )


@pytest.mark.asyncio
async def test_list_alerts_with_segment(alert_service: AlertService) -> None:
    seg_id = uuid.uuid4()
    alert_service.segment_repo.get_by_id.return_value = dummy_segment()
    alert_service.alert_repo.get_all.return_value = [dummy_alert()]

    alerts = await alert_service.list_alerts(segment_id=seg_id)
    assert len(alerts) == 1
    alert_service.segment_repo.get_by_id.assert_called_once_with(seg_id)
    alert_service.alert_repo.get_all.assert_called_once_with(
        segment_id=seg_id, status=None, severity=None, alert_type=None, skip=0, limit=100
    )


@pytest.mark.asyncio
async def test_list_alerts_invalid_segment(alert_service: AlertService) -> None:
    alert_service.segment_repo.get_by_id.return_value = None
    with pytest.raises(SegmentNotFoundError):
        await alert_service.list_alerts(segment_id=uuid.uuid4())


@pytest.mark.asyncio
async def test_get_alert_found(alert_service: AlertService) -> None:
    alert = dummy_alert()
    alert_service.alert_repo.get_by_id.return_value = alert

    result = await alert_service.get_alert(alert.id)
    assert result == alert
    alert_service.alert_repo.get_by_id.assert_called_once_with(alert.id)


@pytest.mark.asyncio
async def test_get_alert_not_found(alert_service: AlertService) -> None:
    alert_service.alert_repo.get_by_id.return_value = None
    with pytest.raises(AlertNotFoundError):
        await alert_service.get_alert(uuid.uuid4())


@pytest.mark.asyncio
async def test_create_alert_success(alert_service: AlertService) -> None:
    seg_id = uuid.uuid4()
    user_id = uuid.uuid4()
    alert_service.segment_repo.get_by_id.return_value = dummy_segment()
    alert = dummy_alert()
    alert_service.alert_repo.create.return_value = alert

    data = AlertCreate(
        segment_id=seg_id,
        title="Title",
        description="Desc",
        alert_type=AlertType.WEATHER,
        severity=AlertSeverity.MEDIUM,
    )
    result = await alert_service.create_alert(data, created_by=user_id)
    
    assert result == alert
    alert_service.segment_repo.get_by_id.assert_called_once_with(seg_id)
    alert_service.alert_repo.create.assert_called_once_with(
        segment_id=seg_id,
        created_by=user_id,
        title="Title",
        description="Desc",
        alert_type=AlertType.WEATHER,
        severity=AlertSeverity.MEDIUM,
        status=AlertStatus.ACTIVE,
    )


@pytest.mark.asyncio
async def test_create_alert_invalid_segment(alert_service: AlertService) -> None:
    alert_service.segment_repo.get_by_id.return_value = None
    data = AlertCreate(
        segment_id=uuid.uuid4(),
        title="Title",
        alert_type=AlertType.WEATHER,
        severity=AlertSeverity.MEDIUM,
    )
    with pytest.raises(SegmentNotFoundError):
        await alert_service.create_alert(data)


@pytest.mark.asyncio
async def test_update_alert_success(alert_service: AlertService) -> None:
    alert = dummy_alert(status=AlertStatus.ACTIVE)
    alert_service.alert_repo.get_by_id.return_value = alert
    alert_service.alert_repo.update.return_value = alert

    data = AlertUpdate(title="New Title", severity=AlertSeverity.CRITICAL)
    await alert_service.update_alert(alert.id, data)
    
    update_kwargs = alert_service.alert_repo.update.call_args.kwargs
    assert update_kwargs["title"] == "New Title"
    assert update_kwargs["severity"] == AlertSeverity.CRITICAL
    assert "description" not in update_kwargs


@pytest.mark.asyncio
async def test_update_alert_not_active(alert_service: AlertService) -> None:
    alert = dummy_alert(status=AlertStatus.RESOLVED)
    alert_service.alert_repo.get_by_id.return_value = alert

    data = AlertUpdate(title="New Title")
    with pytest.raises(AlertNotActiveError):
        await alert_service.update_alert(alert.id, data)


@pytest.mark.asyncio
async def test_resolve_alert_success(alert_service: AlertService) -> None:
    alert = dummy_alert(status=AlertStatus.ACTIVE)
    alert_service.alert_repo.get_by_id.return_value = alert
    alert_service.alert_repo.update.return_value = alert

    await alert_service.resolve_alert(alert.id)
    
    update_kwargs = alert_service.alert_repo.update.call_args.kwargs
    assert update_kwargs["status"] == AlertStatus.RESOLVED
    assert "resolved_at" in update_kwargs


@pytest.mark.asyncio
async def test_resolve_alert_not_active(alert_service: AlertService) -> None:
    alert = dummy_alert(status=AlertStatus.DISMISSED)
    alert_service.alert_repo.get_by_id.return_value = alert

    with pytest.raises(AlertNotActiveError):
        await alert_service.resolve_alert(alert.id)


@pytest.mark.asyncio
async def test_dismiss_alert_success(alert_service: AlertService) -> None:
    alert = dummy_alert(status=AlertStatus.ACTIVE)
    alert_service.alert_repo.get_by_id.return_value = alert
    alert_service.alert_repo.update.return_value = alert

    await alert_service.dismiss_alert(alert.id)
    
    update_kwargs = alert_service.alert_repo.update.call_args.kwargs
    assert update_kwargs["status"] == AlertStatus.DISMISSED
    assert "resolved_at" in update_kwargs


@pytest.mark.asyncio
async def test_delete_alert(alert_service: AlertService) -> None:
    alert = dummy_alert()
    alert_service.alert_repo.get_by_id.return_value = alert

    await alert_service.delete_alert(alert.id)
    alert_service.alert_repo.soft_delete.assert_called_once_with(alert)

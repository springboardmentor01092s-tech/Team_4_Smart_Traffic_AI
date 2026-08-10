"""
tests/test_analytics/test_analytics_service.py
"""
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AnalyticsInvalidBucketError,
    AnalyticsRangeExceededError,
    InvalidDateRangeError,
    SegmentNotFoundError,
)
from app.models.alert import AlertSeverity, AlertType
from app.models.prediction import PredictionStatus
from app.models.segment import CongestionLevel, SegmentStatus
from app.repositories.alert_repository import AlertRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.services.analytics_service import AnalyticsService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def analytics_service(test_db: AsyncSession) -> AnalyticsService:
    return AnalyticsService(
        ReadingRepository(test_db),
        AlertRepository(test_db),
        SegmentRepository(test_db),
        PredictionRepository(test_db),
    )


async def test_get_summary(analytics_service: AnalyticsService) -> None:
    # We just test the method executes successfully since we rely on repo logic
    summary = await analytics_service.get_summary()
    assert summary.total_segments == 0
    assert summary.active_alerts == 0
    assert summary.critical_alerts == 0
    assert isinstance(summary.congestion_distribution, dict)


async def test_get_congestion_heatmap(analytics_service: AnalyticsService) -> None:
    heatmap = await analytics_service.get_congestion_heatmap()
    assert isinstance(heatmap, list)


async def test_get_peak_hour_averages_invalid_dates(analytics_service: AnalyticsService) -> None:
    now = datetime.now(UTC)
    with pytest.raises(InvalidDateRangeError):
        await analytics_service.get_peak_hour_averages(from_dt=now, to_dt=now - timedelta(days=1))

    with pytest.raises(AnalyticsRangeExceededError):
        await analytics_service.get_peak_hour_averages(
            from_dt=now - timedelta(days=32), to_dt=now
        )


async def test_get_segment_history_not_found(analytics_service: AnalyticsService) -> None:
    with pytest.raises(SegmentNotFoundError):
        await analytics_service.get_segment_history(
            uuid.uuid4(), None, None, 60
        )


async def test_get_segment_trends_not_found(analytics_service: AnalyticsService) -> None:
    with pytest.raises(SegmentNotFoundError):
        await analytics_service.get_segment_trends(uuid.uuid4())


async def test_get_full_report_invalid_dates(analytics_service: AnalyticsService) -> None:
    now = datetime.now(UTC)
    with pytest.raises(InvalidDateRangeError):
        await analytics_service.get_full_report(from_dt=now, to_dt=now - timedelta(days=1))

    with pytest.raises(AnalyticsRangeExceededError):
        await analytics_service.get_full_report(
            from_dt=now - timedelta(days=32), to_dt=now
        )

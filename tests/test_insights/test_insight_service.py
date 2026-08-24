import uuid
import pytest
from datetime import UTC, datetime, timedelta

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.prediction import PredictionStatus, TrafficPrediction
from app.models.segment import CongestionLevel
from app.schemas.analytics import HourlyTrend, SegmentTrendsRead, TrendDirection
from app.schemas.insight import InsightType, RiskLevel
from app.schemas.route import RouteComparisonRead
from app.services.insight_service import InsightService

@pytest.mark.asyncio
async def test_insight_insufficient_data(monkeypatch):
    from unittest.mock import AsyncMock
    mock_reading_repo = AsyncMock()
    mock_reading_repo.get_latest_for_segment.return_value = None
    
    service = InsightService(
        reading_repo=mock_reading_repo,
        prediction_repo=AsyncMock(),
        alert_repo=AsyncMock(),
        route_repo=AsyncMock(),
        analytics_service=AsyncMock(),
        route_service=AsyncMock(),
    )
    
    seg_id = uuid.uuid4()
    insight = await service.generate_segment_insight(seg_id)
    assert insight.insight_type == InsightType.INSUFFICIENT_DATA
    assert insight.risk_level == RiskLevel.LOW

@pytest.mark.asyncio
async def test_insight_critical_incident(monkeypatch):
    from unittest.mock import AsyncMock
    from app.models.reading import TrafficReading
    
    mock_reading_repo = AsyncMock()
    mock_reading_repo.get_latest_for_segment.return_value = TrafficReading(
        id=uuid.uuid4(), segment_id=uuid.uuid4(), congestion_level=CongestionLevel.HEAVY
    )
    
    mock_analytics_service = AsyncMock()
    mock_analytics_service.get_segment_trends.return_value = SegmentTrendsRead(
        segment_id=uuid.uuid4(),
        hourly_trends=[
            HourlyTrend(
                hour_of_day=10, 
                current_avg_vehicle_count=100.0, 
                prior_avg_vehicle_count=50.0, 
                delta_percent=50.0, 
                trend_direction=TrendDirection.INCREASING
            )
        ]
    )
    
    mock_alert_repo = AsyncMock()
    mock_alert_repo.get_all.return_value = [
        Alert(id=uuid.uuid4(), title="Test", severity=AlertSeverity.CRITICAL, alert_type=AlertType.ACCIDENT, status=AlertStatus.ACTIVE)
    ]
    
    service = InsightService(
        reading_repo=mock_reading_repo,
        prediction_repo=AsyncMock(),
        alert_repo=mock_alert_repo,
        route_repo=AsyncMock(),
        analytics_service=mock_analytics_service,
        route_service=AsyncMock(),
    )
    
    seg_id = uuid.uuid4()
    insight = await service.generate_segment_insight(seg_id)
    assert insight.insight_type == InsightType.INCIDENT_RISK
    assert insight.risk_level == RiskLevel.CRITICAL
    assert len(insight.evidence) > 0

@pytest.mark.asyncio
async def test_insight_reroute_recommendation(monkeypatch):
    from unittest.mock import AsyncMock
    from app.models.reading import TrafficReading
    
    mock_reading_repo = AsyncMock()
    mock_reading_repo.get_latest_for_segment.return_value = TrafficReading(
        id=uuid.uuid4(), segment_id=uuid.uuid4(), congestion_level=CongestionLevel.HEAVY
    )
    
    mock_analytics_service = AsyncMock()
    mock_analytics_service.get_segment_trends.return_value = SegmentTrendsRead(
        segment_id=uuid.uuid4(),
        hourly_trends=[]
    )
    
    mock_alert_repo = AsyncMock()
    mock_alert_repo.get_all.return_value = []
    
    now = datetime.now(UTC)
    mock_prediction_repo = AsyncMock()
    mock_prediction_repo.get_upcoming_for_segment.return_value = [
        TrafficPrediction(
            id=uuid.uuid4(), 
            segment_id=uuid.uuid4(), 
            status=PredictionStatus.COMPLETED, 
            prediction_for=now + timedelta(hours=1),
            horizon_minutes=60,
            predicted_congestion_level=CongestionLevel.STANDSTILL
        )
    ]
    
    mock_route_repo = AsyncMock()
    # Mocking multiple routes, to trigger len(routes) > 1
    class DummyRoute:
        def __init__(self, id):
            self.id = id
            
    r1 = DummyRoute(uuid.uuid4())
    r2 = DummyRoute(uuid.uuid4())
    mock_route_repo.get_routes_by_segment_id.return_value = [r1, r2]
    # Recommend a route that does not contain this segment (alternate route available)
    mock_route_repo.get_segment_ids_for_route.return_value = [uuid.uuid4()]
    
    mock_route_service = AsyncMock()
    mock_route_service.compare_routes.return_value = RouteComparisonRead(
        recommended_route_id=r2.id,
        routes=[]
    )
    
    service = InsightService(
        reading_repo=mock_reading_repo,
        prediction_repo=mock_prediction_repo,
        alert_repo=mock_alert_repo,
        route_repo=mock_route_repo,
        analytics_service=mock_analytics_service,
        route_service=mock_route_service,
    )
    
    seg_id = uuid.uuid4()
    insight = await service.generate_segment_insight(seg_id)
    assert insight.insight_type == InsightType.REROUTE_RECOMMENDATION
    assert insight.risk_level == RiskLevel.HIGH
    
@pytest.mark.asyncio
async def test_insight_predictive_warning_increasing(monkeypatch):
    from unittest.mock import AsyncMock
    from app.models.reading import TrafficReading
    
    mock_reading_repo = AsyncMock()
    mock_reading_repo.get_latest_for_segment.return_value = TrafficReading(
        id=uuid.uuid4(), segment_id=uuid.uuid4(), congestion_level=CongestionLevel.HEAVY
    )
    
    mock_analytics_service = AsyncMock()
    mock_analytics_service.get_segment_trends.return_value = SegmentTrendsRead(
        segment_id=uuid.uuid4(),
        hourly_trends=[
            HourlyTrend(
                hour_of_day=10, 
                current_avg_vehicle_count=100.0, 
                prior_avg_vehicle_count=50.0, 
                delta_percent=50.0, 
                trend_direction=TrendDirection.INCREASING
            )
        ]
    )
    
    mock_alert_repo = AsyncMock()
    mock_alert_repo.get_all.return_value = []
    
    mock_prediction_repo = AsyncMock()
    mock_prediction_repo.get_upcoming_for_segment.return_value = []
    
    mock_route_repo = AsyncMock()
    mock_route_repo.get_routes_by_segment_id.return_value = []
    
    service = InsightService(
        reading_repo=mock_reading_repo,
        prediction_repo=mock_prediction_repo,
        alert_repo=mock_alert_repo,
        route_repo=mock_route_repo,
        analytics_service=mock_analytics_service,
        route_service=AsyncMock(),
    )
    
    seg_id = uuid.uuid4()
    insight = await service.generate_segment_insight(seg_id)
    assert insight.insight_type == InsightType.PREDICTIVE_WARNING
    assert insight.risk_level == RiskLevel.HIGH
    assert insight.title == "Worsening Congestion"

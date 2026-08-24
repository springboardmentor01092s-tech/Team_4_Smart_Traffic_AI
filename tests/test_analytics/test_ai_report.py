import uuid
import pytest
from datetime import UTC, datetime, timedelta
from httpx import AsyncClient

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.segment import CongestionLevel
from app.schemas.insight import InsightType, RiskLevel, TrafficInsightRead
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import FullReportRead, PredictionReportRead

@pytest.mark.asyncio
async def test_ai_report_candidate_selection_priority(monkeypatch):
    """
    Verify that candidate selection logic bounds the segment list to 10
    and prioritizes Critical > High > Standstill > Heavy.
    """
    from unittest.mock import AsyncMock
    
    mock_reading_repo = AsyncMock()
    mock_alert_repo = AsyncMock()
    mock_prediction_repo = AsyncMock()
    mock_segment_repo = AsyncMock()
    
    mock_insight_service = AsyncMock()
    
    # 5 segments with Critical alert
    critical_ids = [uuid.uuid4() for _ in range(5)]
    # 5 segments with High alert
    high_ids = [uuid.uuid4() for _ in range(5)]
    # 5 segments with Standstill
    standstill_ids = [uuid.uuid4() for _ in range(5)]
    
    alerts = []
    for sid in critical_ids:
        alerts.append(Alert(id=uuid.uuid4(), segment_id=sid, severity=AlertSeverity.CRITICAL, status=AlertStatus.ACTIVE))
    for sid in high_ids:
        alerts.append(Alert(id=uuid.uuid4(), segment_id=sid, severity=AlertSeverity.HIGH, status=AlertStatus.ACTIVE))
        
    mock_alert_repo.get_all.return_value = alerts
    
    readings = []
    class DummyReading:
        def __init__(self, sid, level):
            self.segment_id = sid
            self.congestion_level = level
            
    for sid in standstill_ids:
        readings.append({"reading": DummyReading(sid, CongestionLevel.STANDSTILL)})
        
    mock_reading_repo.get_latest_per_segment.return_value = readings
    mock_reading_repo.get_hourly_averages.return_value = []
    
    # Also mock full_report and prediction report logic correctly
    mock_prediction_repo.get_all.return_value = []
    
    async def get_full_report(*args, **kwargs):
        return FullReportRead(
            report_from=datetime.now(UTC),
            report_to=datetime.now(UTC),
            active_segment_count=0,
            active_alerts_by_severity={},
            congestion_distribution={},
            prediction_completion_rate=0.0,
            busiest_hour=None
        )
        
    service = AnalyticsService(
        reading_repo=mock_reading_repo,
        alert_repo=mock_alert_repo,
        segment_repo=mock_segment_repo,
        prediction_repo=mock_prediction_repo,
    )
    
    monkeypatch.setattr(service, "get_full_report", get_full_report)
    
    # Generate mock insights so it doesn't fail
    async def gen_insight(seg_id):
        return TrafficInsightRead(
            segment_id=seg_id,
            insight_type=InsightType.TRAFFIC_TREND,
            risk_level=RiskLevel.LOW,
            title="Stable",
            recommendation="None",
            evidence=[],
            generated_at=datetime.now(UTC)
        )
    mock_insight_service.generate_segment_insight.side_effect = gen_insight
    
    report = await service.get_ai_report(insight_service=mock_insight_service)
    
    assert len(report.insights) == 10
    
    # We generated 15 candidates total (5 critical, 5 high, 5 standstill).
    # Since we sort by score DESC, the top 10 should consist of all 5 critical, and all 5 high.
    # We check that no standstill segments were included.
    selected_ids = {i.segment_id for i in report.insights}
    for sid in standstill_ids:
        assert sid not in selected_ids

@pytest.mark.asyncio
async def test_get_ai_report_api_smoke(client: AsyncClient, admin_user, monkeypatch):
    from tests.conftest import login_user
    from app.services.analytics_service import AnalyticsService
    from app.schemas.analytics import AITrafficReportRead, TrendDirection
    
    token = await login_user(client, "admin@example.com", "AdminPass1")
    
    async def mock_get_ai_report(*args, **kwargs):
        return AITrafficReportRead(
            generated_at=datetime.now(UTC),
            report_from=datetime.now(UTC) - timedelta(days=1),
            report_to=datetime.now(UTC),
            active_segment_count=10,
            congestion_distribution={CongestionLevel.FREE_FLOW: 10},
            active_alerts_by_severity={AlertSeverity.CRITICAL: 0},
            total_predictions=100,
            prediction_completion_rate=0.9,
            trend_distribution={TrendDirection.STABLE: 24},
            insights=[]
        )
        
    monkeypatch.setattr(AnalyticsService, "get_ai_report", mock_get_ai_report)
    
    response = await client.get(
        "/api/v1/analytics/ai-report",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "traffic_summary" not in data # flattened
    assert "active_segment_count" in data
    assert "insights" in data
    assert "trend_distribution" in data
    assert "active_alerts_by_severity" in data

@pytest.mark.asyncio
async def test_get_ai_report_api_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/analytics/ai-report")
    assert response.status_code == 403

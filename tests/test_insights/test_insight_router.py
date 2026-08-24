import uuid
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_segment_insight_unauthorized(client: AsyncClient):
    seg_id = uuid.uuid4()
    response = await client.get(f"/api/v1/insights/segment/{seg_id}")
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_get_segment_insight_mocked(client: AsyncClient, admin_user, monkeypatch):
    from app.services.insight_service import InsightService
    from app.schemas.insight import TrafficInsightRead, InsightType, RiskLevel
    from datetime import UTC, datetime
    from tests.conftest import login_user
    
    admin_token = await login_user(client, "admin@example.com", "AdminPass1")
    
    seg_id = uuid.uuid4()
    
    async def mock_generate_segment_insight(self, segment_id: uuid.UUID) -> TrafficInsightRead:
        return TrafficInsightRead(
            segment_id=segment_id,
            insight_type=InsightType.TRAFFIC_TREND,
            risk_level=RiskLevel.LOW,
            title="Stable Free Flow Conditions",
            recommendation="No immediate action required.",
            evidence=["Current traffic condition is FREE_FLOW."],
            generated_at=datetime.now(UTC),
        )
        
    monkeypatch.setattr(InsightService, "generate_segment_insight", mock_generate_segment_insight)
    
    response = await client.get(
        f"/api/v1/insights/segment/{seg_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["segment_id"] == str(seg_id)
    assert data["insight_type"] == "TRAFFIC_TREND"
    assert data["risk_level"] == "LOW"
    assert "evidence" in data

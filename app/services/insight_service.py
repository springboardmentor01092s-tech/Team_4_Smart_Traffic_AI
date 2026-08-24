import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.models.alert import AlertSeverity
from app.models.prediction import PredictionStatus
from app.models.segment import CongestionLevel
from app.repositories.alert_repository import AlertRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.route_repository import RouteRepository
from app.schemas.analytics import TrendDirection
from app.schemas.insight import InsightType, RiskLevel, TrafficInsightRead
from app.services.analytics_service import AnalyticsService
from app.services.route_service import RouteService
from app.core.exceptions import SegmentNotFoundError, NoViableRouteError

logger = get_logger(__name__)

# Severity mapping for easier comparisons
_SEVERITY_RANK = {
    AlertSeverity.LOW: 1,
    AlertSeverity.MEDIUM: 2,
    AlertSeverity.HIGH: 3,
    AlertSeverity.CRITICAL: 4,
}

_CONGESTION_RANK = {
    CongestionLevel.FREE_FLOW: 0,
    CongestionLevel.LIGHT: 1,
    CongestionLevel.MODERATE: 2,
    CongestionLevel.HEAVY: 3,
    CongestionLevel.STANDSTILL: 4,
}

class InsightService:
    def __init__(
        self,
        reading_repo: ReadingRepository,
        prediction_repo: PredictionRepository,
        alert_repo: AlertRepository,
        route_repo: RouteRepository,
        analytics_service: AnalyticsService,
        route_service: RouteService,
    ) -> None:
        self._reading_repo = reading_repo
        self._prediction_repo = prediction_repo
        self._alert_repo = alert_repo
        self._route_repo = route_repo
        self._analytics_service = analytics_service
        self._route_service = route_service

    async def generate_segment_insight(self, segment_id: uuid.UUID) -> TrafficInsightRead:
        """
        Generate a structured traffic insight for a given segment.
        Combines current readings, historical trends, upcoming predictions,
        active alerts, and route intelligence.
        """
        now = datetime.now(UTC)
        evidence: list[str] = []
        
        # 1. Current Reading
        current_reading = await self._reading_repo.get_latest_for_segment(segment_id)
        if current_reading is None:
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.INSUFFICIENT_DATA,
                risk_level=RiskLevel.LOW,
                title="Insufficient Data",
                recommendation="Wait for traffic sensors to report data.",
                evidence=["No current traffic reading available for this segment."],
                generated_at=now,
            )

        current_level = current_reading.congestion_level
        evidence.append(f"Current traffic condition is {current_level.value}.")
        
        # 2. Historical Trend
        trend_direction = TrendDirection.STABLE
        try:
            trends = await self._analytics_service.get_segment_trends(segment_id)
            if trends.hourly_trends:
                # Use the most recent hourly trend
                latest_trend = trends.hourly_trends[0]
                trend_direction = latest_trend.trend_direction
                evidence.append(f"Traffic trend over the last hour is {trend_direction.value}.")
        except SegmentNotFoundError:
            pass
            
        # 3. Active Alerts
        active_alerts = await self._alert_repo.get_all(segment_id=segment_id)
        critical_alerts = [a for a in active_alerts if a.severity == AlertSeverity.CRITICAL]
        high_alerts = [a for a in active_alerts if a.severity == AlertSeverity.HIGH]
        if critical_alerts:
            evidence.append(f"CRITICAL alert active: {critical_alerts[0].title}.")
        elif high_alerts:
            evidence.append(f"HIGH severity alert active: {high_alerts[0].title}.")
            
        # 4. Predictions (Freshness: status == COMPLETED, prediction_for > now, < now + 3 hours)
        upcoming_preds = await self._prediction_repo.get_upcoming_for_segment(segment_id)
        valid_prediction = None
        for p in upcoming_preds:
            if p.status == PredictionStatus.COMPLETED and now < p.prediction_for < now + timedelta(hours=3):
                valid_prediction = p
                break
                
        if valid_prediction and valid_prediction.predicted_congestion_level:
            evidence.append(f"Model predicts {valid_prediction.predicted_congestion_level.value} within the next 3 hours.")
            
        # 5. Route Intelligence
        routes = await self._route_repo.get_routes_by_segment_id(segment_id)
        has_alternate_route = False
        if len(routes) > 1:
            try:
                route_comparison = await self._route_service.compare_routes([r.id for r in routes])
                recommended_route_id = route_comparison.recommended_route_id
                
                # Check if the recommended route DOES NOT contain this segment
                recommended_route_segments = await self._route_repo.get_segment_ids_for_route(recommended_route_id)
                if segment_id not in recommended_route_segments:
                    has_alternate_route = True
                    evidence.append("A faster alternate route is available and recommended.")
            except NoViableRouteError:
                pass

        # ── Deterministic Rule Engine ──
        
        # Rule 1: CRITICAL Incident
        if critical_alerts:
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.INCIDENT_RISK,
                risk_level=RiskLevel.CRITICAL,
                title="Critical Incident Active",
                recommendation="Immediately dispatch emergency response and block segment access.",
                evidence=evidence,
                generated_at=now,
            )
            
        # Rule 2: HIGH Reroute Recommendation
        predicted_severe = valid_prediction and _CONGESTION_RANK.get(valid_prediction.predicted_congestion_level, 0) >= _CONGESTION_RANK[CongestionLevel.HEAVY]
        current_severe = _CONGESTION_RANK.get(current_level, 0) >= _CONGESTION_RANK[CongestionLevel.HEAVY]
        
        if (predicted_severe or current_severe) and has_alternate_route:
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.REROUTE_RECOMMENDATION,
                risk_level=RiskLevel.HIGH,
                title="Severe Congestion - Reroute Advised",
                recommendation="Recommend alternate routes to drivers approaching this segment.",
                evidence=evidence,
                generated_at=now,
            )
            
        # Rule 3: HIGH Predictive Warning
        if current_severe and trend_direction == TrendDirection.INCREASING:
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.PREDICTIVE_WARNING,
                risk_level=RiskLevel.HIGH,
                title="Worsening Congestion",
                recommendation="Prioritize monitoring of this segment; congestion is heavy and increasing.",
                evidence=evidence,
                generated_at=now,
            )
            
        if predicted_severe:
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.PREDICTIVE_WARNING,
                risk_level=RiskLevel.HIGH,
                title="Predicted Severe Congestion",
                recommendation="Prepare for impending severe congestion; consider proactive traffic management.",
                evidence=evidence,
                generated_at=now,
            )
            
        if high_alerts:
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.INCIDENT_RISK,
                risk_level=RiskLevel.HIGH,
                title="High Risk Alert Active",
                recommendation="Investigate active high-severity alert.",
                evidence=evidence,
                generated_at=now,
            )
            
        # Rule 4: MEDIUM Trend Insight
        current_moderate = _CONGESTION_RANK.get(current_level, 0) == _CONGESTION_RANK[CongestionLevel.MODERATE]
        if current_moderate and trend_direction == TrendDirection.INCREASING:
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.TRAFFIC_TREND,
                risk_level=RiskLevel.MEDIUM,
                title="Moderate Congestion Trending Up",
                recommendation="Monitor segment for potential bottlenecks as traffic is increasing.",
                evidence=evidence,
                generated_at=now,
            )
            
        if current_moderate or (_CONGESTION_RANK.get(current_level, 0) >= _CONGESTION_RANK[CongestionLevel.MODERATE]):
            return TrafficInsightRead(
                segment_id=segment_id,
                insight_type=InsightType.CONGESTION_RISK,
                risk_level=RiskLevel.MEDIUM,
                title="Moderate Congestion",
                recommendation="Maintain standard monitoring. Conditions are currently manageable.",
                evidence=evidence,
                generated_at=now,
            )
            
        # Rule 5: LOW Informational Insight
        return TrafficInsightRead(
            segment_id=segment_id,
            insight_type=InsightType.TRAFFIC_TREND,
            risk_level=RiskLevel.LOW,
            title="Stable Free Flow Conditions",
            recommendation="No immediate action required.",
            evidence=evidence,
            generated_at=now,
        )

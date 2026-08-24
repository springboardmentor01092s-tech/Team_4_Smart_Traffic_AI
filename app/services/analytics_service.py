"""
app/services/analytics_service.py

Business logic for the Analytics module.
"""
from collections import defaultdict
from datetime import UTC, datetime, timedelta
import uuid

from app.core.config import settings
from app.core.exceptions import (
    AnalyticsInvalidBucketError,
    AnalyticsRangeExceededError,
    InvalidDateRangeError,
    SegmentNotFoundError,
)
from app.models.alert import AlertSeverity
from app.models.segment import CongestionLevel
from app.models.prediction import PredictionStatus
from app.repositories.alert_repository import AlertRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.schemas.analytics import (
    AnalyticsSummaryRead,
    FullReportRead,
    HeatmapItemRead,
    HistoryBucketRead,
    HourlyTrend,
    PeakHourRead,
    PredictionReportItem,
    PredictionReportRead,
    SegmentTrendsRead,
    TrendDirection,
    AITrafficReportRead
)
from app.schemas.insight import TrafficInsightRead

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.services.insight_service import InsightService


class AnalyticsService:
    def __init__(
        self,
        reading_repo: ReadingRepository,
        alert_repo: AlertRepository,
        segment_repo: SegmentRepository,
        prediction_repo: PredictionRepository,
    ) -> None:
        self.reading_repo = reading_repo
        self.alert_repo = alert_repo
        self.segment_repo = segment_repo
        self.prediction_repo = prediction_repo

    def _classify_trend(self, delta: float | None) -> TrendDirection:
        """Classify a trend delta into a Direction enum."""
        if delta is None:
            return TrendDirection.STABLE
        if delta >= settings.trend_increasing_threshold_percent:
            return TrendDirection.INCREASING
        if delta <= settings.trend_decreasing_threshold_percent:
            return TrendDirection.DECREASING
        return TrendDirection.STABLE

    async def get_summary(self) -> AnalyticsSummaryRead:
        total_segments = await self.segment_repo.count_all_non_deleted()
        active_alerts = await self.alert_repo.get_active_count()
        critical_alerts = await self.alert_repo.get_active_by_severity(AlertSeverity.CRITICAL)
        congestion_distribution = await self.reading_repo.count_by_congestion_level()

        return AnalyticsSummaryRead(
            total_segments=total_segments,
            active_alerts=active_alerts,
            critical_alerts=critical_alerts,
            congestion_distribution=congestion_distribution,
        )

    async def get_congestion_heatmap(self) -> list[HeatmapItemRead]:
        items = await self.reading_repo.get_latest_per_segment()
        return [
            HeatmapItemRead(
                segment_id=item["segment_id"],
                congestion_level=item["reading"].congestion_level,
                vehicle_count=item["reading"].vehicle_count,
                average_speed_kmh=item["reading"].average_speed_kmh,
                recorded_at=item["reading"].recorded_at,
                start_latitude=item["segment"].start_latitude,
                start_longitude=item["segment"].start_longitude,
                end_latitude=item["segment"].end_latitude,
                end_longitude=item["segment"].end_longitude,
            )
            for item in items
        ]

    async def get_peak_hour_averages(
        self, from_dt: datetime | None = None, to_dt: datetime | None = None
    ) -> list[PeakHourRead]:
        if from_dt and to_dt:
            if from_dt >= to_dt:
                raise InvalidDateRangeError()
            if (to_dt - from_dt).days > 30:
                raise AnalyticsRangeExceededError(max_days=30)

        averages = await self.reading_repo.get_hourly_averages(from_dt=from_dt, to_dt=to_dt)
        return [
            PeakHourRead(
                hour=item["hour"],
                avg_vehicle_count=item["avg_vehicle_count"],
                avg_speed_kmh=item["avg_speed_kmh"],
            )
            for item in averages
        ]

    async def get_segment_history(
        self,
        segment_id: uuid.UUID,
        from_dt: datetime | None,
        to_dt: datetime | None,
        bucket_minutes: int,
    ) -> list[HistoryBucketRead]:
        segment = await self.segment_repo.get_by_id(segment_id)
        if not segment:
            raise SegmentNotFoundError(segment_id)

        if from_dt and to_dt:
            if from_dt >= to_dt:
                raise InvalidDateRangeError()
            if (to_dt - from_dt).days > 90:
                raise AnalyticsRangeExceededError(max_days=90)

        if bucket_minutes not in {5, 15, 30, 60}:
            raise AnalyticsInvalidBucketError(bucket_minutes)

        readings = await self.reading_repo.get_all(
            segment_id=segment_id,
            from_dt=from_dt,
            to_dt=to_dt,
            limit=1000000,
        )

        if not readings:
            return []

        # Group by bucket
        buckets = defaultdict(list)
        for r in readings:
            dt = r.recorded_at
            # round down to nearest bucket_minutes
            minute = (dt.minute // bucket_minutes) * bucket_minutes
            bucket_start = dt.replace(minute=minute, second=0, microsecond=0)
            buckets[bucket_start].append(r)

        history = []
        for bucket_start in sorted(buckets.keys()):
            bucket_readings = buckets[bucket_start]
            count = len(bucket_readings)
            avg_vc = sum(r.vehicle_count for r in bucket_readings) / count
            avg_speed = sum(r.average_speed_kmh for r in bucket_readings) / count
            history.append(
                HistoryBucketRead(
                    bucket_start=bucket_start,
                    avg_vehicle_count=avg_vc,
                    avg_speed_kmh=avg_speed,
                    reading_count=count,
                )
            )

        return history

    async def get_segment_trends(self, segment_id: uuid.UUID) -> SegmentTrendsRead:
        segment = await self.segment_repo.get_by_id(segment_id)
        if not segment:
            raise SegmentNotFoundError(segment_id)

        now = datetime.now(UTC)
        current_to = now
        current_from = now - timedelta(days=7)
        prior_to = current_from
        prior_from = prior_to - timedelta(days=7)

        current_avgs = await self.reading_repo.get_hourly_averages(
            segment_id=segment_id, from_dt=current_from, to_dt=current_to
        )
        prior_avgs = await self.reading_repo.get_hourly_averages(
            segment_id=segment_id, from_dt=prior_from, to_dt=prior_to
        )

        current_by_hour = defaultdict(list)
        for item in current_avgs:
            current_by_hour[item["hour"].hour].append(item["avg_vehicle_count"])

        prior_by_hour = defaultdict(list)
        for item in prior_avgs:
            prior_by_hour[item["hour"].hour].append(item["avg_vehicle_count"])

        trends = []
        for hour in range(24):
            curr_vals = current_by_hour.get(hour, [])
            prior_vals = prior_by_hour.get(hour, [])
            curr_avg = sum(curr_vals) / len(curr_vals) if curr_vals else 0.0
            prior_avg = sum(prior_vals) / len(prior_vals) if prior_vals else 0.0
            delta = None
            if prior_avg > 0:
                delta = ((curr_avg - prior_avg) / prior_avg) * 100.0

            trends.append(
                HourlyTrend(
                    hour_of_day=hour,
                    current_avg_vehicle_count=curr_avg,
                    prior_avg_vehicle_count=prior_avg,
                    delta_percent=delta,
                    trend_direction=self._classify_trend(delta),
                )
            )

        return SegmentTrendsRead(segment_id=segment_id, hourly_trends=trends)

    async def get_full_report(self, from_dt: datetime, to_dt: datetime) -> FullReportRead:
        if from_dt >= to_dt:
            raise InvalidDateRangeError()
        if (to_dt - from_dt).days > 30:
            raise AnalyticsRangeExceededError(max_days=30)

        active_segment_count = await self.segment_repo.count_all_non_deleted()
        
        # 1. Alert Summary by Severity within date range
        alerts = await self.alert_repo.get_all(limit=1000000)
        filtered_alerts = []
        for a in alerts:
            created_dt = a.created_at.replace(tzinfo=UTC) if a.created_at.tzinfo is None else a.created_at
            if from_dt <= created_dt <= to_dt:
                filtered_alerts.append(a)
        
        active_alerts_by_severity = {severity: 0 for severity in AlertSeverity}
        for a in filtered_alerts:
            # Re-read: The spec says "active alert summary by severity". Does it mean status=ACTIVE?
            if a.status.value == "ACTIVE":
                active_alerts_by_severity[a.severity] += 1
                
        # Wait, if it says "active alert summary by severity", it likely means just currently active alerts. 
        # But we pass from_dt and to_dt... maybe for congestion dist and busiest hour.
        # Let's count all alerts created in the period that are active, or just all active alerts?
        # I'll just use the filtered ones. 

        # 2. Congestion Distribution (from readings in date range)
        readings = await self.reading_repo.get_all(from_dt=from_dt, to_dt=to_dt, limit=1000000)
        congestion_dist = {level: 0 for level in CongestionLevel}
        for r in readings:
            congestion_dist[r.congestion_level] += 1

        # 3. Prediction Completion Rate
        predictions = await self.prediction_repo.get_all(limit=1000000)
        completed = 0
        total = 0
        for p in predictions:
            created_dt = p.created_at.replace(tzinfo=UTC) if p.created_at.tzinfo is None else p.created_at
            if from_dt <= created_dt <= to_dt:
                total += 1
                if p.status == PredictionStatus.COMPLETED:
                    completed += 1
        completion_rate = completed / total if total > 0 else 0.0

        # 4. Busiest hour band
        averages = await self.reading_repo.get_hourly_averages(from_dt=from_dt, to_dt=to_dt)
        busiest_hour = None
        if averages:
            busiest_item = max(averages, key=lambda x: x["avg_vehicle_count"])
            busiest_hour = busiest_item["hour"]

        return FullReportRead(
            report_from=from_dt,
            report_to=to_dt,
            active_segment_count=active_segment_count,
            active_alerts_by_severity=active_alerts_by_severity,
            congestion_distribution=congestion_dist,
            prediction_completion_rate=completion_rate,
            busiest_hour=busiest_hour,
        )

    async def get_prediction_report(
        self,
        segment_id: uuid.UUID | None = None,
        status: PredictionStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> PredictionReportRead:
        """
        Return a prediction performance report.

        Uses PredictionRepository directly (no AnalyticsRepository).
        No fabricated accuracy metrics — only real prediction data.

        Args:
            segment_id: Optional filter by segment UUID.
            status:     Optional filter by prediction status.
            skip:       Pagination offset.
            limit:      Maximum predictions to include.

        Returns:
            PredictionReportRead with counts, completion rate, and prediction list.
        """
        predictions = await self.prediction_repo.get_all(
            segment_id=segment_id,
            status=status,
            skip=skip,
            limit=limit,
        )

        # Count totals from the filtered result set
        total = len(predictions)
        completed = sum(1 for p in predictions if p.status == PredictionStatus.COMPLETED)
        failed = sum(1 for p in predictions if p.status == PredictionStatus.FAILED)
        pending = sum(1 for p in predictions if p.status == PredictionStatus.PENDING)
        completion_rate = completed / total if total > 0 else 0.0

        items = [
            PredictionReportItem(
                id=p.id,
                segment_id=p.segment_id,
                status=p.status,
                model_version=p.model_version,
                prediction_for=p.prediction_for,
                horizon_minutes=p.horizon_minutes,
                predicted_congestion_level=p.predicted_congestion_level,
                predicted_vehicle_count=p.predicted_vehicle_count,
                predicted_avg_speed_kmh=p.predicted_avg_speed_kmh,
                confidence_score=p.confidence_score,
                requested_at=p.requested_at,
                completed_at=p.completed_at,
            )
            for p in predictions
        ]

        return PredictionReportRead(
            total_predictions=total,
            completed=completed,
            failed=failed,
            pending=pending,
            completion_rate=round(completion_rate, 4),
            predictions=items,
        )

    async def get_ai_report(
        self,
        insight_service: "InsightService",
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> AITrafficReportRead:
        now = datetime.now(UTC)
        if to_dt is None:
            to_dt = now
        if from_dt is None:
            from_dt = to_dt - timedelta(days=1)
            
        # 1. Reuse existing aggregation for traffic & alerts
        full_report = await self.get_full_report(from_dt, to_dt)
        
        # 2. Reuse predictions
        # We need total predictions and completion rate from the full_report
        # full_report already computes this!
        
        # 3. System-wide trend distribution
        prior_to = from_dt
        prior_from = prior_to - (to_dt - from_dt)
        
        # get_hourly_averages across all segments
        current_avgs = await self.reading_repo.get_hourly_averages(from_dt=from_dt, to_dt=to_dt)
        prior_avgs = await self.reading_repo.get_hourly_averages(from_dt=prior_from, to_dt=prior_to)
        
        current_by_hour = defaultdict(list)
        for item in current_avgs:
            current_by_hour[item["hour"].hour].append(item["avg_vehicle_count"])

        prior_by_hour = defaultdict(list)
        for item in prior_avgs:
            prior_by_hour[item["hour"].hour].append(item["avg_vehicle_count"])

        trend_distribution = {td: 0 for td in TrendDirection}
        for hour in range(24):
            curr_vals = current_by_hour.get(hour, [])
            prior_vals = prior_by_hour.get(hour, [])
            curr_avg = sum(curr_vals) / len(curr_vals) if curr_vals else 0.0
            prior_avg = sum(prior_vals) / len(prior_vals) if prior_vals else 0.0
            delta = None
            if prior_avg > 0:
                delta = ((curr_avg - prior_avg) / prior_avg) * 100.0
            
            direction = self._classify_trend(delta)
            trend_distribution[direction] += 1
            
        # 4. Bounded Insight Generation Candidate Selection
        candidates: dict[uuid.UUID, int] = {}
        
        # a. Active Alerts
        from app.models.alert import AlertStatus
        active_alerts = await self.alert_repo.get_all(status=AlertStatus.ACTIVE) # get all active
        for a in active_alerts:
            # We must resolve priority: CRITICAL=5, HIGH=4
            score = 0
            if a.severity == AlertSeverity.CRITICAL:
                score = 5
            elif a.severity == AlertSeverity.HIGH:
                score = 4
                
            if score > 0:
                candidates[a.segment_id] = max(candidates.get(a.segment_id, 0), score)
                
        # b. Current Congestion
        latest_readings = await self.reading_repo.get_latest_per_segment()
        for item in latest_readings:
            reading = item["reading"]
            seg_id = reading.segment_id
            score = 0
            if reading.congestion_level == CongestionLevel.STANDSTILL:
                score = 3
            elif reading.congestion_level == CongestionLevel.HEAVY:
                score = 2
                
            if score > 0:
                candidates[seg_id] = max(candidates.get(seg_id, 0), score)
                
        # Sort candidates deterministically: score DESC, segment_id ASC
        sorted_candidates = sorted(
            candidates.items(),
            key=lambda x: (-x[1], str(x[0]))
        )
        
        # Take max 10
        top_segment_ids = [c[0] for c in sorted_candidates[:10]]
        
        insights: list[TrafficInsightRead] = []
        for seg_id in top_segment_ids:
            insight = await insight_service.generate_segment_insight(seg_id)
            insights.append(insight)
            
        # Sort generated insights deterministically
        _RISK_RANK = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1
        }
        
        _TYPE_RANK = {
            "INCIDENT_RISK": 5,
            "PREDICTIVE_WARNING": 4,
            "REROUTE_RECOMMENDATION": 3,
            "CONGESTION_RISK": 2,
            "TRAFFIC_TREND": 2,
            "INSUFFICIENT_DATA": 1
        }
        
        insights.sort(
            key=lambda i: (
                -_RISK_RANK.get(i.risk_level.value, 0),
                -_TYPE_RANK.get(i.insight_type.value, 0),
                str(i.segment_id)
            )
        )
        
        # Also need total predictions - we have it in prediction_report if we need it, but the FullReportRead gives completion_rate
        # To get total predictions in this timeframe without getting full report again
        # We can just fetch prediction report for counts
        pred_report = await self.get_prediction_report(limit=1) 
        # Wait, get_prediction_report does not take from_dt to_dt. Let's do it manually for the date range
        predictions = await self.prediction_repo.get_all(limit=1000000)
        filtered_preds = [p for p in predictions if from_dt <= p.created_at <= to_dt]
        total_predictions = len(filtered_preds)

        return AITrafficReportRead(
            generated_at=now,
            report_from=from_dt,
            report_to=to_dt,
            active_segment_count=full_report.active_segment_count,
            congestion_distribution=full_report.congestion_distribution,
            active_alerts_by_severity=full_report.active_alerts_by_severity,
            total_predictions=total_predictions,
            prediction_completion_rate=full_report.prediction_completion_rate,
            trend_distribution=trend_distribution,
            insights=insights
        )

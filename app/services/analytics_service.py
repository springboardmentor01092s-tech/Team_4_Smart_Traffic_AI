"""
app/services/analytics_service.py

Business logic for the Analytics module.
"""
from collections import defaultdict
from datetime import UTC, datetime, timedelta
import uuid

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
    SegmentTrendsRead,
)


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
        filtered_alerts = [a for a in alerts if from_dt <= a.created_at <= to_dt]
        
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
        filtered_preds = [p for p in predictions if from_dt <= p.created_at <= to_dt]
        pred_total = len(filtered_preds)
        pred_completed = sum(1 for p in filtered_preds if p.status == PredictionStatus.COMPLETED)
        completion_rate = pred_completed / pred_total if pred_total > 0 else 0.0

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

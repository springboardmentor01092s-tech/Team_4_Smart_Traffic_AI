import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.reading import TrafficReading
from app.models.segment import CongestionLevel, TrafficSegment


class ReadingRepository:
    """
    Repository for managing TrafficReading entities.
    Readings are immutable and append-only. No soft-delete logic is required.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, reading_id: int) -> TrafficReading | None:
        return await self.session.get(TrafficReading, reading_id)

    async def get_latest_for_segment(self, segment_id: uuid.UUID) -> TrafficReading | None:
        stmt = (
            select(TrafficReading)
            .where(TrafficReading.segment_id == segment_id)
            .order_by(desc(TrafficReading.recorded_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()



    async def get_all(
        self,
        segment_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        congestion_level: CongestionLevel | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TrafficReading]:
        stmt = select(TrafficReading)
        if segment_id:
            stmt = stmt.where(TrafficReading.segment_id == segment_id)
        if from_dt:
            stmt = stmt.where(TrafficReading.recorded_at >= from_dt)
        if to_dt:
            stmt = stmt.where(TrafficReading.recorded_at <= to_dt)
        if congestion_level:
            stmt = stmt.where(TrafficReading.congestion_level == congestion_level)
            
        stmt = stmt.order_by(desc(TrafficReading.recorded_at)).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(
        self,
        segment_id: uuid.UUID,
        vehicle_count: int,
        average_speed_kmh: float,
        congestion_level: CongestionLevel,
        occupancy_percent: float | None,
        recorded_at: datetime,
    ) -> TrafficReading:
        reading = TrafficReading(
            segment_id=segment_id,
            vehicle_count=vehicle_count,
            average_speed_kmh=average_speed_kmh,
            congestion_level=congestion_level,
            occupancy_percent=occupancy_percent,
            recorded_at=recorded_at,
        )
        self.session.add(reading)
        await self.session.flush()
        return reading

    async def get_hourly_averages(
        self,
        segment_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
    ) -> Sequence[dict]:
        """
        Calculates hourly averages of vehicle_count and average_speed_kmh.
        """
        hour_expr = func.date_trunc('hour', TrafficReading.recorded_at).label('hour_bucket')
        
        stmt = select(
            hour_expr,
            func.avg(TrafficReading.vehicle_count).label('avg_vehicle_count'),
            func.avg(TrafficReading.average_speed_kmh).label('avg_speed_kmh')
        )
        
        if segment_id:
            stmt = stmt.where(TrafficReading.segment_id == segment_id)
        if from_dt:
            stmt = stmt.where(TrafficReading.recorded_at >= from_dt)
        if to_dt:
            stmt = stmt.where(TrafficReading.recorded_at <= to_dt)
            
        stmt = stmt.group_by(hour_expr).order_by(hour_expr)
        
        result = await self.session.execute(stmt)
        return [
            {
                "hour": row.hour_bucket,
                "avg_vehicle_count": float(row.avg_vehicle_count) if row.avg_vehicle_count is not None else 0.0,
                "avg_speed_kmh": float(row.avg_speed_kmh) if row.avg_speed_kmh is not None else 0.0,
            }
            for row in result.all()
        ]

    async def get_latest_per_segment(self) -> Sequence[dict]:
        """
        Returns the latest reading for each active (non-deleted) segment.
        """
        # We need a subquery to find the latest reading per segment
        # Using ROW_NUMBER() is standard SQL and works in both PostgreSQL and SQLite
        subq = (
            select(
                TrafficReading,
                func.row_number().over(
                    partition_by=TrafficReading.segment_id,
                    order_by=desc(TrafficReading.recorded_at)
                ).label('rn')
            )
            .subquery()
        )
        
        # We need to map the subquery back to the TrafficReading entity
        reading_alias = aliased(TrafficReading, subq)
        
        stmt = (
            select(reading_alias)
            .join(TrafficSegment, TrafficSegment.id == reading_alias.segment_id)
            .where(TrafficSegment.deleted_at.is_(None))
            .where(subq.c.rn == 1)
        )
        result = await self.session.execute(stmt)
        readings = result.scalars().all()
        return [
            {
                "segment_id": r.segment_id,
                "reading": r
            }
            for r in readings
        ]

    async def count_by_congestion_level(self) -> dict[str, int]:
        """
        Counts the number of latest readings per congestion level across all active segments.
        """
        subq = (
            select(
                TrafficReading.segment_id,
                TrafficReading.congestion_level,
                func.row_number().over(
                    partition_by=TrafficReading.segment_id,
                    order_by=desc(TrafficReading.recorded_at)
                ).label('rn')
            )
            .subquery()
        )
        
        stmt = (
            select(subq.c.congestion_level, func.count().label('count'))
            .join(TrafficSegment, TrafficSegment.id == subq.c.segment_id)
            .where(TrafficSegment.deleted_at.is_(None))
            .where(subq.c.rn == 1)
            .group_by(subq.c.congestion_level)
        )
        
        result = await self.session.execute(stmt)
        counts = {level.value: 0 for level in CongestionLevel}
        for row in result.all():
            counts[row.congestion_level.value] = row.count
            
        return counts

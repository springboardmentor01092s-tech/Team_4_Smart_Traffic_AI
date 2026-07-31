from datetime import datetime, timezone
import uuid
from collections.abc import Sequence

from app.core.exceptions import ReadingNotFoundError, SegmentNotFoundError, InvalidReadingTimeError
from app.models.reading import TrafficReading
from app.models.segment import CongestionLevel
from app.repositories.reading_repository import ReadingRepository
from app.repositories.segment_repository import SegmentRepository
from app.schemas.reading import ReadingCreate


class ReadingService:
    def __init__(
        self, reading_repo: ReadingRepository, segment_repo: SegmentRepository
    ) -> None:
        self.reading_repo = reading_repo
        self.segment_repo = segment_repo

    async def submit_reading(self, data: ReadingCreate) -> TrafficReading:
        segment = await self.segment_repo.get_by_id(data.segment_id)
        if not segment:
            raise SegmentNotFoundError(data.segment_id)

        # Ensure recorded_at is timezone-aware before comparison
        now = datetime.now(timezone.utc)
        recorded_at_utc = data.recorded_at
        if recorded_at_utc.tzinfo is None:
            recorded_at_utc = recorded_at_utc.replace(tzinfo=timezone.utc)

        if recorded_at_utc > now:
            raise InvalidReadingTimeError()

        return await self.reading_repo.create(
            segment_id=data.segment_id,
            vehicle_count=data.vehicle_count,
            average_speed_kmh=data.average_speed_kmh,
            congestion_level=data.congestion_level,
            occupancy_percent=data.occupancy_percent,
            recorded_at=data.recorded_at,
        )

    async def list_readings(
        self,
        segment_id: uuid.UUID | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        congestion_level: CongestionLevel | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TrafficReading]:
        if from_dt and to_dt and from_dt >= to_dt:
            # We don't have a specific exception for this, so we'll just let it return empty 
            # or could raise a generic ValueError. The spec says "Validates from_dt < to_dt if both provided"
            # Since no specific exception is given, returning empty or ValueError is fine.
            raise ValueError("from_dt must be before to_dt")

        if segment_id:
            segment = await self.segment_repo.get_by_id(segment_id)
            if not segment:
                raise SegmentNotFoundError(segment_id)

        return await self.reading_repo.get_all(
            segment_id=segment_id,
            from_dt=from_dt,
            to_dt=to_dt,
            congestion_level=congestion_level,
            skip=skip,
            limit=limit,
        )

    async def get_reading(self, reading_id: int) -> TrafficReading:
        reading = await self.reading_repo.get_by_id(reading_id)
        if not reading:
            raise ReadingNotFoundError(reading_id)
        return reading

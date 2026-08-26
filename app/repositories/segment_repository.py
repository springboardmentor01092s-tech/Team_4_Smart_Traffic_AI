"""
app/repositories/segment_repository.py

Data access layer for the TrafficSegment entity.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.segment import SegmentStatus, TrafficSegment

logger = get_logger(__name__)


class SegmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, segment_id: uuid.UUID) -> TrafficSegment | None:
        result = await self._db.execute(
            select(TrafficSegment).where(
                TrafficSegment.id == segment_id,
                TrafficSegment.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_ids(
        self, segment_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, TrafficSegment]:
        """
        Batch-fetches active (non-deleted) segments by UUID.
        Returns a mapping of {segment_id: TrafficSegment}.
        """
        if not segment_ids:
            return {}
        result = await self._db.execute(
            select(TrafficSegment).where(
                TrafficSegment.id.in_(segment_ids),
                TrafficSegment.deleted_at.is_(None),
            )
        )
        segments = result.scalars().all()
        return {s.id: s for s in segments}

    async def get_all(
        self,
        *,
        status: SegmentStatus | None = None,
        camera_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TrafficSegment]:
        query = select(TrafficSegment).where(TrafficSegment.deleted_at.is_(None))
        if status is not None:
            query = query.where(TrafficSegment.status == status)
        if camera_id is not None:
            query = query.where(TrafficSegment.camera_id == camera_id)
            
        query = query.order_by(TrafficSegment.created_at.desc()).offset(skip).limit(limit)
        result = await self._db.execute(query)
        return result.scalars().all()

    async def create(
        self,
        *,
        name: str,
        start_point: str,
        end_point: str,
        start_latitude: float,
        start_longitude: float,
        end_latitude: float,
        end_longitude: float,
        length_km: float,
        speed_limit_kmh: int,
        camera_id: uuid.UUID | None = None,
        status: SegmentStatus = SegmentStatus.ACTIVE,
    ) -> TrafficSegment:
        segment = TrafficSegment(
            name=name,
            start_point=start_point,
            end_point=end_point,
            start_latitude=start_latitude,
            start_longitude=start_longitude,
            end_latitude=end_latitude,
            end_longitude=end_longitude,
            length_km=length_km,
            speed_limit_kmh=speed_limit_kmh,
            camera_id=camera_id,
            status=status,
        )
        self._db.add(segment)
        await self._db.flush()
        await self._db.refresh(segment)
        logger.info("TrafficSegment created | id=%s", segment.id)
        return segment

    async def update(self, segment: TrafficSegment, **fields: object) -> TrafficSegment:
        for field, value in fields.items():
            setattr(segment, field, value)
        self._db.add(segment)
        await self._db.flush()
        await self._db.refresh(segment)
        logger.info("TrafficSegment updated | id=%s", segment.id)
        return segment

    async def soft_delete(self, segment: TrafficSegment) -> None:
        now = datetime.now(UTC)
        segment.deleted_at = now
        segment.updated_at = now
        self._db.add(segment)
        await self._db.flush()
        logger.warning("TrafficSegment soft-deleted | id=%s", segment.id)

    async def count_all_non_deleted(self) -> int:
        result = await self._db.execute(
            select(func.count(TrafficSegment.id)).where(TrafficSegment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none() or 0

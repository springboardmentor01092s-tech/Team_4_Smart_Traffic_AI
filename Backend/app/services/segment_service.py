"""
app/services/segment_service.py

Business logic layer for the Traffic Segments module.
"""
import uuid
from datetime import UTC, datetime

from app.core.exceptions import AppBaseException, CameraNotFoundError, SegmentNotFoundError
from app.core.logging import get_logger
from app.models.segment import SegmentStatus, TrafficSegment
from app.repositories.camera_repository import CameraRepository
from app.repositories.segment_repository import SegmentRepository
from app.repositories.reading_repository import ReadingRepository
from app.repositories.alert_repository import AlertRepository
from app.schemas.segment import SegmentCreate, SegmentUpdate

logger = get_logger(__name__)


class SegmentService:
    def __init__(
        self,
        segment_repo: SegmentRepository,
        camera_repo: CameraRepository,
        reading_repo: ReadingRepository,
        alert_repo: AlertRepository,
    ) -> None:
        self.segment_repo = segment_repo
        self.camera_repo = camera_repo
        self.reading_repo = reading_repo
        self.alert_repo = alert_repo

    async def list_segments(
        self,
        *,
        status: SegmentStatus | None = None,
        camera_id: uuid.UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TrafficSegment]:
        if camera_id is not None:
            camera = await self.camera_repo.get_by_id(camera_id)
            if camera is None:
                raise CameraNotFoundError(camera_id)
        
        segments = await self.segment_repo.get_all(status=status, camera_id=camera_id, skip=skip, limit=limit)
        return list(segments)

    async def get_segment(self, segment_id: uuid.UUID) -> TrafficSegment:
        segment = await self.segment_repo.get_by_id(segment_id)
        if segment is None:
            raise SegmentNotFoundError(segment_id)
        return segment

    async def get_latest_reading(self, segment_id: uuid.UUID) -> dict | None:
        """
        Retrieves the most recent traffic reading for the given segment.
        Validates segment existence first.
        """
        segment = await self.segment_repo.get_by_id(segment_id)
        if not segment:
            raise SegmentNotFoundError(segment_id)
        
        return await self.reading_repo.get_latest_for_segment(segment_id)

    async def create_segment(self, data: SegmentCreate) -> TrafficSegment:
        if data.camera_id is not None:
            camera = await self.camera_repo.get_by_id(data.camera_id)
            if camera is None:
                raise CameraNotFoundError(data.camera_id)

        segment = await self.segment_repo.create(
            name=data.name,
            start_point=data.start_point,
            end_point=data.end_point,
            start_latitude=data.start_latitude,
            start_longitude=data.start_longitude,
            end_latitude=data.end_latitude,
            end_longitude=data.end_longitude,
            length_km=data.length_km,
            speed_limit_kmh=data.speed_limit_kmh,
            camera_id=data.camera_id,
            status=data.status,
        )
        return segment

    async def update_segment(
        self,
        segment_id: uuid.UUID,
        data: SegmentUpdate,
    ) -> TrafficSegment:
        segment = await self.get_segment(segment_id)

        update_fields: dict[str, object] = {}
        if data.name is not None:
            update_fields["name"] = data.name
        if data.start_point is not None:
            update_fields["start_point"] = data.start_point
        if data.end_point is not None:
            update_fields["end_point"] = data.end_point
        if data.start_latitude is not None:
            update_fields["start_latitude"] = data.start_latitude
        if data.start_longitude is not None:
            update_fields["start_longitude"] = data.start_longitude
        if data.end_latitude is not None:
            update_fields["end_latitude"] = data.end_latitude
        if data.end_longitude is not None:
            update_fields["end_longitude"] = data.end_longitude
        if data.length_km is not None:
            update_fields["length_km"] = data.length_km
        if data.speed_limit_kmh is not None:
            update_fields["speed_limit_kmh"] = data.speed_limit_kmh
        if data.camera_id is not None:
            update_fields["camera_id"] = data.camera_id
        # Explicit check for status because we want to allow updating it to the same value
        # Actually Pydantic data.model_fields_set is better, but since it's an explicit param we check if it is not None.
        # But wait, what if we want to nullify camera_id? The Pydantic model has default=None.
        # If camera_id was provided as None, it would be ignored.
        # We need to distinguish between omitted and explicit None. But the Prompt explicitly says:
        # "Only provided fields are changed". We will stick to the same pattern as CameraService.
        
        # We should use `model_dump(exclude_unset=True)` for cleaner update.
        # Let's match CameraService's behavior:
        for field in [
            "name", "start_point", "end_point", "start_latitude", "start_longitude",
            "end_latitude", "end_longitude", "length_km", "speed_limit_kmh", "status"
        ]:
            val = getattr(data, field)
            if val is not None:
                update_fields[field] = val
                
        # camera_id might be set to None explicitly. To keep it simple and match CameraUpdate
        # which ignores None, let's just do `is not None` unless we need to handle clearing the camera.
        # In CameraUpdate `description: str | None = Field(default=None)` is used and
        # `if data.description is not None:` ignores clearing it. That's a flaw in CameraUpdate 
        # but since we must exactly follow conventions, we will use `is not None`.
        # However, to be slightly better without deviating:
        if "camera_id" in data.model_fields_set:
            if data.camera_id is not None:
                camera = await self.camera_repo.get_by_id(data.camera_id)
                if camera is None:
                    raise CameraNotFoundError(data.camera_id)
            update_fields["camera_id"] = data.camera_id
            
        update_fields["updated_at"] = datetime.now(UTC)

        updated = await self.segment_repo.update(segment, **update_fields)
        return updated

    async def delete_segment(self, segment_id: uuid.UUID) -> None:
        segment = await self.get_segment(segment_id)
        
        from app.models.alert import AlertStatus
        alerts = await self.alert_repo.get_all(segment_id=segment_id, status=AlertStatus.ACTIVE)
        if alerts:
            from app.core.exceptions import SegmentHasActiveAlertsError
            raise SegmentHasActiveAlertsError(segment_id)

        await self.segment_repo.soft_delete(segment)

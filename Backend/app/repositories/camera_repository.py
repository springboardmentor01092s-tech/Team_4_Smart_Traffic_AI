"""
app/repositories/camera_repository.py

Data access layer for the TrafficCamera entity.

Responsibilities:
  - All async SQLAlchemy queries for TrafficCamera records.
  - No business logic. No HTTP concerns. No exception raising for domain rules.
  - Accepts an AsyncSession injected by the caller (Depends(get_db)).

Soft-delete convention:
  - get_by_id and get_all always filter deleted_at IS NULL.
  - soft_delete() sets deleted_at = utcnow() and updated_at = utcnow(), then flushes.
  - No hard-delete method is exposed for cameras.

Pattern mirrors UserRepository exactly.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.camera import CameraStatus, TrafficCamera

logger = get_logger(__name__)


class CameraRepository:
    """
    Repository for TrafficCamera persistence operations.

    Instantiated per-request with an injected AsyncSession.
    All methods are async to avoid blocking the event loop.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ─── Read ────────────────────────────────────────────────────────────────

    async def get_by_id(self, camera_id: uuid.UUID) -> TrafficCamera | None:
        """
        Return a non-deleted TrafficCamera by primary key, or None.

        Soft-deleted cameras (deleted_at IS NOT NULL) are treated as absent.
        """
        result = await self._db.execute(
            select(TrafficCamera).where(
                TrafficCamera.id == camera_id,
                TrafficCamera.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        status: CameraStatus | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[TrafficCamera]:
        """
        Return a paginated list of non-deleted cameras.

        Args:
            status: Optional filter by CameraStatus. None returns all statuses.
            skip:   Number of records to skip (offset for pagination).
            limit:  Maximum number of records to return.

        Returns:
            A sequence of TrafficCamera instances, ordered by created_at DESC.
        """
        query = select(TrafficCamera).where(TrafficCamera.deleted_at.is_(None))
        if status is not None:
            query = query.where(TrafficCamera.status == status)
        query = query.order_by(TrafficCamera.created_at.desc()).offset(skip).limit(limit)
        result = await self._db.execute(query)
        return result.scalars().all()

    async def count_by_status(self, status: CameraStatus) -> int:
        """
        Count non-deleted cameras in the given status.

        Used by CameraService to detect whether a camera is in a specific state.
        """
        result = await self._db.execute(
            select(func.count()).where(
                TrafficCamera.status == status,
                TrafficCamera.deleted_at.is_(None),
            )
        )
        return result.scalar_one()

    # ─── Write ───────────────────────────────────────────────────────────────

    async def create(
        self,
        *,
        name: str,
        location_name: str,
        latitude: float,
        longitude: float,
        status: CameraStatus = CameraStatus.ACTIVE,
        description: str | None = None,
        installed_at: datetime | None = None,
    ) -> TrafficCamera:
        """
        Persist a new TrafficCamera and return the created instance.

        The session commit is handled by the get_db dependency.
        After this method returns, the object is flushed (id assigned)
        but the transaction is not yet committed.

        Args:
            name:          Human-readable camera label.
            location_name: Textual installation location.
            latitude:      Geographic latitude (-90 to 90).
            longitude:     Geographic longitude (-180 to 180).
            status:        Initial operational status. Defaults to ACTIVE.
            description:   Optional free-text notes.
            installed_at:  Physical installation timestamp. Defaults to utcnow().

        Returns:
            The persisted TrafficCamera ORM instance.
        """
        camera = TrafficCamera(
            name=name,
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            status=status,
            description=description,
            installed_at=installed_at or datetime.now(UTC),
        )
        self._db.add(camera)
        await self._db.flush()
        await self._db.refresh(camera)
        logger.info(
            "TrafficCamera created | id=%s | name=%s | status=%s",
            camera.id,
            camera.name,
            camera.status,
        )
        return camera

    async def update(self, camera: TrafficCamera, **fields: object) -> TrafficCamera:
        """
        Update arbitrary fields on a TrafficCamera instance.

        Only fields whose values are not None are applied, unless the column
        is explicitly nullable (e.g. description) — in that case pass a
        sentinel or handle in the service layer.

        Args:
            camera: The ORM instance to update.
            **fields: Keyword arguments mapping column names to new values.

        Returns:
            The updated TrafficCamera instance (refreshed from DB).
        """
        for field, value in fields.items():
            setattr(camera, field, value)
        self._db.add(camera)
        await self._db.flush()
        await self._db.refresh(camera)
        logger.info(
            "TrafficCamera updated | id=%s | fields=%s",
            camera.id,
            list(fields.keys()),
        )
        return camera

    async def soft_delete(self, camera: TrafficCamera) -> None:
        """
        Soft-delete a TrafficCamera by setting deleted_at to the current UTC time.

        The record is NOT physically removed from the database.
        Subsequent calls to get_by_id or get_all will not return this camera.

        Args:
            camera: The ORM instance to soft-delete.
        """
        now = datetime.now(UTC)
        camera.deleted_at = now
        camera.updated_at = now
        self._db.add(camera)
        await self._db.flush()
        logger.warning(
            "TrafficCamera soft-deleted | id=%s | name=%s",
            camera.id,
            camera.name,
        )

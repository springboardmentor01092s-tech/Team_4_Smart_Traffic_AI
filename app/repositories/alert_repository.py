"""
app/repositories/alert_repository.py

Data access layer for the TrafficAlert entity.
"""
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType

logger = get_logger(__name__)


class AlertRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, alert_id: uuid.UUID) -> Alert | None:
        result = await self._db.execute(
            select(Alert).where(
                Alert.id == alert_id,
                Alert.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        segment_id: uuid.UUID | None = None,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Alert]:
        query = select(Alert).where(Alert.deleted_at.is_(None))
        if segment_id is not None:
            query = query.where(Alert.segment_id == segment_id)
        if status is not None:
            query = query.where(Alert.status == status)
        if severity is not None:
            query = query.where(Alert.severity == severity)
        if alert_type is not None:
            query = query.where(Alert.alert_type == alert_type)
            
        query = query.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
        result = await self._db.execute(query)
        return result.scalars().all()

    async def get_active_count(self) -> int:
        result = await self._db.execute(
            select(func.count()).where(
                Alert.status == AlertStatus.ACTIVE,
                Alert.deleted_at.is_(None)
            )
        )
        return result.scalar_one()

    async def get_active_by_severity(self, severity: AlertSeverity) -> int:
        result = await self._db.execute(
            select(func.count()).where(
                Alert.status == AlertStatus.ACTIVE,
                Alert.severity == severity,
                Alert.deleted_at.is_(None)
            )
        )
        return result.scalar_one()

    async def count_active_by_severities(self) -> dict[AlertSeverity, int]:
        """Return active alert counts grouped by severity directly via SQL."""
        stmt = (
            select(Alert.severity, func.count().label("cnt"))
            .where(
                Alert.status == AlertStatus.ACTIVE,
                Alert.deleted_at.is_(None),
            )
            .group_by(Alert.severity)
        )
        result = await self._db.execute(stmt)
        counts = {severity: 0 for severity in AlertSeverity}
        for row in result.all():
            counts[row.severity] = row.cnt
        return counts

    async def get_active_for_segment_and_type(
        self, segment_id: uuid.UUID, alert_type: AlertType, for_update: bool = False
    ) -> Alert | None:
        """Fetch the active alert for a segment and type, optionally locking the row."""
        query = select(Alert).where(
            Alert.segment_id == segment_id,
            Alert.alert_type == alert_type,
            Alert.status == AlertStatus.ACTIVE,
            Alert.deleted_at.is_(None)
        )
        
        if for_update and self._db.bind.dialect.name != "sqlite":
            query = query.with_for_update()
            
        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        segment_id: uuid.UUID,
        created_by: uuid.UUID | None = None,
        title: str,
        description: str | None = None,
        alert_type: AlertType,
        severity: AlertSeverity,
        status: AlertStatus = AlertStatus.ACTIVE,
    ) -> Alert:
        alert = Alert(
            segment_id=segment_id,
            created_by=created_by,
            title=title,
            description=description,
            alert_type=alert_type,
            severity=severity,
            status=status,
        )
        self._db.add(alert)
        await self._db.flush()
        await self._db.refresh(alert)
        logger.info("TrafficAlert created | id=%s", alert.id)
        return alert

    async def update(self, alert: Alert, **fields: object) -> Alert:
        for field, value in fields.items():
            setattr(alert, field, value)
        self._db.add(alert)
        await self._db.flush()
        await self._db.refresh(alert)
        logger.info("TrafficAlert updated | id=%s", alert.id)
        return alert

    async def soft_delete(self, alert: Alert) -> None:
        now = datetime.now(UTC)
        alert.deleted_at = now
        alert.updated_at = now
        self._db.add(alert)
        await self._db.flush()
        logger.warning("TrafficAlert soft-deleted | id=%s", alert.id)

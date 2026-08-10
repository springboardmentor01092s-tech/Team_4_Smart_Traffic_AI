"""
app/services/alert_service.py

Business logic layer for the Traffic Alerts module.
"""
import uuid
from datetime import UTC, datetime

from app.core.exceptions import (
    AlertNotActiveError,
    AlertNotFoundError,
    SegmentNotFoundError,
)
from app.core.logging import get_logger
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.repositories.alert_repository import AlertRepository
from app.repositories.segment_repository import SegmentRepository
from app.schemas.alert import AlertCreate, AlertUpdate

logger = get_logger(__name__)


class AlertService:
    def __init__(
        self,
        alert_repo: AlertRepository,
        segment_repo: SegmentRepository,
    ) -> None:
        self.alert_repo = alert_repo
        self.segment_repo = segment_repo

    async def list_alerts(
        self,
        *,
        segment_id: uuid.UUID | None = None,
        status: AlertStatus | None = None,
        severity: AlertSeverity | None = None,
        alert_type: AlertType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Alert]:
        if segment_id is not None:
            segment = await self.segment_repo.get_by_id(segment_id)
            if segment is None:
                raise SegmentNotFoundError(segment_id)
        
        alerts = await self.alert_repo.get_all(
            segment_id=segment_id,
            status=status,
            severity=severity,
            alert_type=alert_type,
            skip=skip,
            limit=limit,
        )
        return list(alerts)

    async def get_alert(self, alert_id: uuid.UUID) -> Alert:
        alert = await self.alert_repo.get_by_id(alert_id)
        if alert is None:
            raise AlertNotFoundError(alert_id)
        return alert

    async def create_alert(
        self,
        data: AlertCreate,
        created_by: uuid.UUID | None = None,
    ) -> Alert:
        segment = await self.segment_repo.get_by_id(data.segment_id)
        if segment is None:
            raise SegmentNotFoundError(data.segment_id)

        alert = await self.alert_repo.create(
            segment_id=data.segment_id,
            created_by=created_by,
            title=data.title,
            description=data.description,
            alert_type=data.alert_type,
            severity=data.severity,
            status=AlertStatus.ACTIVE,
        )
        logger.info("Alert created | id=%s type=%s severity=%s", alert.id, alert.alert_type, alert.severity)
        return alert

    async def update_alert(
        self,
        alert_id: uuid.UUID,
        data: AlertUpdate,
    ) -> Alert:
        alert = await self.get_alert(alert_id)

        if alert.status != AlertStatus.ACTIVE:
            raise AlertNotActiveError(alert_id)

        update_fields: dict[str, object] = {}
        if data.title is not None:
            update_fields["title"] = data.title
        if data.description is not None:
            update_fields["description"] = data.description
        if data.severity is not None:
            update_fields["severity"] = data.severity

        update_fields["updated_at"] = datetime.now(UTC)

        updated = await self.alert_repo.update(alert, **update_fields)
        return updated

    async def resolve_alert(self, alert_id: uuid.UUID) -> Alert:
        alert = await self.get_alert(alert_id)
        if alert.status != AlertStatus.ACTIVE:
            raise AlertNotActiveError(alert_id)

        now = datetime.now(UTC)
        updated = await self.alert_repo.update(
            alert,
            status=AlertStatus.RESOLVED,
            resolved_at=now,
            updated_at=now,
        )
        logger.info("Alert resolved | id=%s", alert.id)
        return updated

    async def dismiss_alert(self, alert_id: uuid.UUID) -> Alert:
        alert = await self.get_alert(alert_id)
        if alert.status != AlertStatus.ACTIVE:
            raise AlertNotActiveError(alert_id)

        now = datetime.now(UTC)
        updated = await self.alert_repo.update(
            alert,
            status=AlertStatus.DISMISSED,
            resolved_at=now,
            updated_at=now,
        )
        logger.info("Alert dismissed | id=%s", alert.id)
        return updated

    async def delete_alert(self, alert_id: uuid.UUID) -> None:
        alert = await self.get_alert(alert_id)
        await self.alert_repo.soft_delete(alert)

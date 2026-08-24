"""
app/services/incident_service.py

Service for handling manual incident reports (e.g. accidents, road closures).
"""
import uuid

from app.core.logging import get_logger
from app.models.alert import AlertType
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertUpdate
from app.schemas.incident import IncidentCreate
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService

logger = get_logger(__name__)


class IncidentService:
    def __init__(
        self,
        alert_service: AlertService,
        notification_service: NotificationService,
    ) -> None:
        self._alert_service = alert_service
        self._notification_service = notification_service

    async def report_incident(self, data: IncidentCreate, user: User) -> None:
        """
        Ingest a manual incident report.
        Idempotent: updates existing alert of the same type on the segment if active.
        """
        # 1. Check for existing active alert
        active_alert = await self._alert_service.alert_repo.get_active_for_segment_and_type(
            segment_id=data.segment_id,
            alert_type=data.incident_type,
            for_update=True
        )

        if not active_alert:
            # Create new
            create_data = AlertCreate(
                segment_id=data.segment_id,
                title=data.title,
                description=data.description,
                alert_type=data.incident_type,
                severity=data.severity,
            )
            alert = await self._alert_service.create_alert(data=create_data, created_by=user.id)
            logger.info("IncidentService: Created new %s alert %s", data.incident_type, alert.id)
            
            # Generate notifications
            await self._notification_service.generate_notifications_for_alert(alert)
        else:
            # Update existing
            update_data = AlertUpdate(
                title=data.title,
                description=data.description,
                severity=data.severity,
            )
            alert = await self._alert_service.update_alert(alert_id=active_alert.id, data=update_data)
            logger.info("IncidentService: Updated existing %s alert %s", data.incident_type, alert.id)
            
            # Also notify on manual update just in case severity increased or details changed
            await self._notification_service.generate_notifications_for_alert(alert)

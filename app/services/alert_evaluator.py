"""
app/services/alert_evaluator.py

Service responsible for evaluating traffic readings and deterministically
generating or updating congestion alerts based on severity rules.
"""

from app.core.logging import get_logger
from app.models.alert import AlertSeverity, AlertType
from app.models.reading import TrafficReading
from app.models.segment import CongestionLevel
from app.services.alert_service import AlertService
from app.services.notification_service import NotificationService
from app.schemas.alert import AlertCreate, AlertUpdate

logger = get_logger(__name__)

SEVERITY_WEIGHT = {
    AlertSeverity.LOW: 1,
    AlertSeverity.MEDIUM: 2,
    AlertSeverity.HIGH: 3,
    AlertSeverity.CRITICAL: 4,
}

class AlertEvaluatorService:
    def __init__(self, alert_service: AlertService, notification_service: NotificationService) -> None:
        self.alert_service = alert_service
        self.notification_service = notification_service

    async def evaluate_reading(self, reading: TrafficReading) -> None:
        """
        Evaluate a reading and create or update a congestion alert if necessary.
        
        Rules:
        - HEAVY -> HIGH congestion alert
        - STANDSTILL -> CRITICAL congestion alert
        - Suppress duplicate active alerts.
        - Escalate existing alert if the new condition is more severe.
        """
        target_severity = None
        if reading.congestion_level == CongestionLevel.HEAVY:
            target_severity = AlertSeverity.HIGH
        elif reading.congestion_level == CongestionLevel.STANDSTILL:
            target_severity = AlertSeverity.CRITICAL
            
        if not target_severity:
            # Non-triggering condition, do nothing
            return

        # Fetch active congestion alert with concurrency protection
        active_alert = await self.alert_service.alert_repo.get_active_for_segment_and_type(
            segment_id=reading.segment_id,
            alert_type=AlertType.CONGESTION,
            for_update=True
        )

        if not active_alert:
            # No active alert, create a new one
            title = f"Congestion Alert: {target_severity.value}"
            description = (
                f"Automated congestion detection. Level: {reading.congestion_level.value}, "
                f"Vehicle Count: {reading.vehicle_count}, Speed: {reading.average_speed_kmh} km/h"
            )
            create_data = AlertCreate(
                segment_id=reading.segment_id,
                title=title,
                description=description,
                alert_type=AlertType.CONGESTION,
                severity=target_severity
            )
            alert = await self.alert_service.create_alert(data=create_data)
            logger.info("AlertEvaluator: Created new %s alert for segment %s", target_severity, reading.segment_id)
            await self.notification_service.generate_notifications_for_alert(alert)
        else:
            # Active alert exists, check if escalation is needed
            current_weight = SEVERITY_WEIGHT[active_alert.severity]
            target_weight = SEVERITY_WEIGHT[target_severity]
            
            if target_weight > current_weight:
                update_data = AlertUpdate(severity=target_severity)
                alert = await self.alert_service.update_alert(alert_id=active_alert.id, data=update_data)
                logger.info("AlertEvaluator: Escalated alert %s to %s", active_alert.id, target_severity)
                await self.notification_service.generate_notifications_for_alert(alert)
            else:
                # Suppress duplicate/unchanged condition
                logger.debug("AlertEvaluator: Suppressed duplicate alert for segment %s", reading.segment_id)

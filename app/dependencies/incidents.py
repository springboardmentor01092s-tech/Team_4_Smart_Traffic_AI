"""
app/dependencies/incidents.py

Dependencies for Incident handling.
"""
from fastapi import Depends

from app.dependencies.alerts import get_alert_service
from app.dependencies.notifications import get_notification_service
from app.services.alert_service import AlertService
from app.services.incident_service import IncidentService
from app.services.notification_service import NotificationService


def get_incident_service(
    alert_service: AlertService = Depends(get_alert_service),
    notification_service: NotificationService = Depends(get_notification_service)
) -> IncidentService:
    return IncidentService(alert_service, notification_service)

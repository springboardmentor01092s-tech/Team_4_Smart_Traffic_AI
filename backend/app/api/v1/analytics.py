from fastapi import APIRouter
from app.services import analytics_service

router = APIRouter()

@router.get("/heatmap")
def heatmap():
    """Returns latest traffic density metrics per junction for heatmap visualizations."""
    return analytics_service.get_heatmap_data()

@router.get("/trends")
def trends(junction_id: str, hours: int = 24):
    """Returns historical traffic density and speed trends for a given junction."""
    return analytics_service.get_trends(junction_id, hours)

@router.get("/summary")
def summary():
    """Returns aggregated system metrics for the traffic controller summary dashboard."""
    return analytics_service.get_summary()

from fastapi import APIRouter
from app.api.v1 import traffic, auth, alerts, analytics

api_router = APIRouter()
api_router.include_router(traffic.router, prefix="/traffic", tags=["traffic"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


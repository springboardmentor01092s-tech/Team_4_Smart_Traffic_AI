"""
app/routers/__init__.py

Centralized router registration.

Extension point for Backend Developer #2:
    Import your routers here and include them in the `api_router`.
    Do not modify `main.py`.
"""
from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router


def get_api_router() -> APIRouter:
    """Return a single APIRouter containing all grouped sub-routers."""
    api_router = APIRouter()

    # Core foundation routes
    api_router.include_router(auth_router)
    api_router.include_router(users_router)

    # ──────────────────────────────────────────────────────────────────────────
    # BUSINESS MODULE ROUTERS — Backend Developer #2
    # ──────────────────────────────────────────────────────────────────────────
    from app.routers.cameras import router as cameras_router  # noqa: PLC0415
    from app.routers.segments import router as segments_router  # noqa: PLC0415
    from app.routers.readings import router as readings_router  # noqa: PLC0415
    from app.routers.alerts import router as alerts_router  # noqa: PLC0415
    from app.routers.predictions import router as predictions_router  # noqa: PLC0415
    from app.routers.routes import router as routes_router  # noqa: PLC0415
    from app.routers.analytics import router as analytics_router  # noqa: PLC0415
    from app.routers.incidents import router as incidents_router  # noqa: PLC0415
    from app.routers.notifications import router as notifications_router  # noqa: PLC0415
    from app.routers.insights import router as insights_router  # noqa: PLC0415

    api_router.include_router(cameras_router)
    api_router.include_router(segments_router)
    api_router.include_router(readings_router)
    api_router.include_router(alerts_router)
    api_router.include_router(predictions_router)
    api_router.include_router(routes_router)
    api_router.include_router(analytics_router)
    api_router.include_router(incidents_router)
    api_router.include_router(notifications_router)
    api_router.include_router(insights_router)

    return api_router

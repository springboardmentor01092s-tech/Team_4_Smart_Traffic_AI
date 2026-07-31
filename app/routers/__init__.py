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

    api_router.include_router(cameras_router)
    api_router.include_router(segments_router)
    api_router.include_router(readings_router)
    api_router.include_router(alerts_router)
    api_router.include_router(predictions_router)

    return api_router


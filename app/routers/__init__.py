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
    # FUTURE MODULE ROUTERS — Backend Developer #2 adds here
    # Example:
    #   from app.routers.traffic import router as traffic_router
    #   api_router.include_router(traffic_router)
    #
    #   from app.routers.alerts import router as alerts_router
    #   api_router.include_router(alerts_router)
    # ──────────────────────────────────────────────────────────────────────────
    
    return api_router

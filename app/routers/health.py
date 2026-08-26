"""
app/routers/health.py

Production health, liveness, and readiness endpoints.

Endpoints:
    GET /api/v1/health       - General system status and metadata (backwards-compatible)
    GET /api/v1/health/live  - Process liveness check for orchestrators / container runtime
    GET /api/v1/health/ready - Readiness check verifying database connectivity
"""
from datetime import UTC, datetime
import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    summary="Health check",
    description="Returns service status and uptime metadata. No authentication required.",
    response_description="Service health status",
)
async def health_check() -> dict:
    """Return backwards-compatible system status metadata."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/live",
    summary="Liveness check",
    description="Indicates whether the application process is alive. Used by Kubernetes/Docker liveness probes.",
    response_description="Process liveness state",
)
async def liveness_check() -> dict:
    """Return immediate process liveness confirmation."""
    return {
        "status": "alive",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/ready",
    summary="Readiness check",
    description="Verifies that the backend can serve requests by checking database connectivity. Returns 503 if database is unreachable.",
    response_description="Service readiness state",
)
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """
    Verify application readiness by executing a lightweight database query.
    Returns HTTP 200 on success, HTTP 503 on database connectivity failure.
    Does not expose sensitive credentials or database connection details.
    """
    try:
        await db.execute(text("SELECT 1"))
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "ready",
                "database": "connected",
                "service": settings.app_name,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception as exc:
        logger.error("Readiness check failed: database connectivity issue: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unready",
                "database": "disconnected",
                "service": settings.app_name,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )

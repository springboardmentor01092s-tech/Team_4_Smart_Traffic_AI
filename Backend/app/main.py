"""
app/main.py

FastAPI application factory for TrafficVision AI.

Design decisions:
  - Uses lifespan context manager (modern FastAPI pattern, replaces on_event).
  - All routers registered under /api/v1 prefix.
  - Exception handlers and middleware registered centrally.
  - The health endpoint lives here (not in a router) to keep it dependency-free.

Extension point for Backend Developer #2:
    Register your routers in `app/routers/__init__.py`.
    You do not need to modify this file.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import register_middleware

# Import all models so SQLAlchemy metadata is populated for Alembic
import app.models  # noqa: F401

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Startup: Initialize logging, log startup info.
    Shutdown: Log clean shutdown.

    Note: Database connections are managed per-request via get_db().
    Connection pool is created lazily on first use.
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    setup_logging()
    logger.info(
        "Starting %s v%s | env=%s | debug=%s",
        settings.app_name,
        settings.app_version,
        settings.app_env,
        settings.debug,
    )
    logger.info(
        "API available at %s | Docs at /docs | ReDoc at /redoc",
        settings.api_v1_prefix,
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down %s", settings.app_name)


def create_application() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.

    Returns a fully configured FastAPI application with:
      - CORS, request ID, and request logging middleware
      - Versioned API routes (/api/v1/...)
      - Centralized exception handlers
      - Custom OpenAPI documentation
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "TrafficVision AI — Backend API\n\n"
            "This API provides authentication and user management for the "
            "TrafficVision AI smart traffic prediction and congestion management system.\n\n"
            "## Authentication\n\n"
            "Use `POST /api/v1/auth/register` to create an account, "
            "then `POST /api/v1/auth/login` to receive a Bearer JWT. "
            "Include it as `Authorization: Bearer <token>` on protected endpoints.\n\n"
            "Click the **Authorize** button 🔒 above to enter your token."
        ),
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        contact={
            "name": "TrafficVision AI Backend Team",
            "email": "backend@trafficvision.ai",
        },
        license_info={"name": "MIT"},
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    register_middleware(app)

    # ── Exception Handlers ───────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── API Routers ──────────────────────────────────────────────────────────
    from app.routers import get_api_router
    
    app.include_router(get_api_router(), prefix=settings.api_v1_prefix)

    # ── Health Endpoint ───────────────────────────────────────────────────────
    @app.get(
        f"{settings.api_v1_prefix}/health",
        tags=["Health"],
        summary="Health check",
        description="Returns service status and uptime. No authentication required.",
        response_description="Service health status",
    )
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    return app


# ── Application singleton ─────────────────────────────────────────────────────
app = create_application()

"""
app/core/middleware.py

ASGI/Starlette middleware for the TrafficVision AI backend.

Middleware layers (applied in registration order, outermost first):
  1. CORSMiddleware  — cross-origin header injection
  2. RequestIDMiddleware — attach X-Request-ID to every request/response
  3. RequestLoggingMiddleware — structured request/response logging

Extension policy: Add new middleware by calling
    app.add_middleware(YourMiddleware, ...)
in main.py BEFORE calling register_middleware(app).
"""
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Attach a unique X-Request-ID header to every request and response.

    - Uses the incoming X-Request-ID if provided (useful for tracing across services).
    - Generates a new UUID v4 otherwise.
    - Stores the ID on request.state.request_id for access in handlers/loggers.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log every HTTP request with method, path, status code, and duration.

    Excludes health-check endpoints to avoid log noise in production.
    """

    _EXCLUDED_PATHS: frozenset[str] = frozenset({"/api/v1/health", "/favicon.ico"})

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()
        request_id = getattr(request.state, "request_id", "-")

        logger.info(
            "→ %s %s | request_id=%s | client=%s",
            request.method,
            request.url.path,
            request_id,
            request.client.host if request.client else "unknown",
        )

        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        log_fn = logger.warning if response.status_code >= 400 else logger.info
        log_fn(
            "← %s %s | status=%d | duration=%.1fms | request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )

        return response


def register_middleware(app: FastAPI) -> None:
    """
    Register all middleware on the FastAPI application.

    Order matters: middleware is applied in REVERSE registration order.
    The last `add_middleware` call becomes the outermost layer.
    """
    # Inner layer: request logging (runs after request ID is assigned)
    app.add_middleware(RequestLoggingMiddleware)

    # Middle layer: request ID assignment
    app.add_middleware(RequestIDMiddleware)

    # Outer layer: CORS (runs first on incoming, last on outgoing)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

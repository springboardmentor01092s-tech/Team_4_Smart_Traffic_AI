"""
app/core/exceptions.py

Custom exception classes and global FastAPI exception handlers.

Design decisions:
  - All domain exceptions inherit from AppBaseException so callers
    can catch them as a single type if needed.
  - HTTP mapping is done only in exception handlers, keeping domain
    exceptions free of HTTP concepts.
  - Handlers return a consistent JSON envelope:
      { "detail": "...", "error_code": "...", "request_id": "..." }

Extension policy:
  Backend Developer #2 should add their own domain exceptions here
  or in a separate module that inherits from AppBaseException.
"""
import logging
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# ─── Base Exception ──────────────────────────────────────────────────────────

class AppBaseException(Exception):
    """
    Base class for all application-specific exceptions.
    Provides a consistent interface: message + optional detail dict.
    """

    def __init__(self, message: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail or {}


# ─── Authentication Exceptions ───────────────────────────────────────────────

class AuthenticationError(AppBaseException):
    """Raised when JWT decoding fails or credentials are invalid."""


class InvalidCredentialsError(AuthenticationError):
    """Raised when email/password combination does not match."""

    def __init__(self) -> None:
        super().__init__("Invalid email or password.")


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT has expired."""

    def __init__(self) -> None:
        super().__init__("Access token has expired.")


class TokenInvalidError(AuthenticationError):
    """Raised when a JWT is malformed or tampered with."""

    def __init__(self) -> None:
        super().__init__("Access token is invalid.")


# ─── Authorization Exceptions ────────────────────────────────────────────────

class PermissionDeniedError(AppBaseException):
    """Raised when an authenticated user lacks the required role."""

    def __init__(self, required_role: str | None = None) -> None:
        msg = "You do not have permission to access this resource."
        if required_role:
            msg = f"This resource requires the '{required_role}' role."
        super().__init__(msg)


# ─── User Exceptions ────────────────────────────────────────────────────────

class UserNotFoundError(AppBaseException):
    """Raised when a user lookup returns no result."""

    def __init__(self, identifier: str = "") -> None:
        super().__init__(f"User not found{': ' + identifier if identifier else '.'}")


class UserAlreadyExistsError(AppBaseException):
    """Raised when attempting to register with an email already in use."""

    def __init__(self, email: str) -> None:
        super().__init__(f"A user with email '{email}' already exists.")


class UserInactiveError(AppBaseException):
    """Raised when an inactive user attempts to authenticate."""

    def __init__(self) -> None:
        super().__init__("This account has been deactivated.")


# ─── Traffic Camera Exceptions ────────────────────────────────────────────────

class CameraNotFoundError(AppBaseException):
    """Raised when a traffic camera lookup returns no result."""

    def __init__(self, camera_id: object = "") -> None:
        super().__init__(f"Traffic camera {camera_id} not found.")


class CameraInUseError(AppBaseException):
    """Raised when a camera cannot be deleted because segments reference it."""

    def __init__(self, camera_id: object = "") -> None:
        super().__init__(
            f"Camera {camera_id} is assigned to active segments and cannot be deleted."
        )


# ─── Traffic Segment Exceptions ────────────────────────────────────────────────

class SegmentNotFoundError(AppBaseException):
    """Raised when a traffic segment lookup returns no result."""

    def __init__(self, segment_id: object = "") -> None:
        super().__init__(f"Traffic segment {segment_id} not found.")


# ─── Traffic Reading Exceptions ────────────────────────────────────────────────

class ReadingNotFoundError(AppBaseException):
    """Raised when a traffic reading lookup returns no result."""

    def __init__(self, reading_id: object = "") -> None:
        super().__init__(f"Traffic reading {reading_id} not found.")


class InvalidReadingTimeError(AppBaseException):
    """Raised when a reading time is in the future."""

    def __init__(self) -> None:
        super().__init__("Reading recorded_at cannot be in the future.")


# ─── Exception Handlers ──────────────────────────────────────────────────────

def _error_response(
    request: Request,
    status_code: int,
    detail: str,
    error_code: str = "ERROR",
) -> JSONResponse:
    """Build a standardized error JSON response."""
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": detail,
            "error_code": error_code,
            "request_id": request_id,
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Catch FastAPI/Starlette HTTP exceptions and reformat them."""
    logger.warning(
        "HTTP %d | %s %s | %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )
    return _error_response(request, exc.status_code, str(exc.detail), "HTTP_ERROR")


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Catch Pydantic validation errors and return a 422 with structured details."""
    errors = exc.errors()
    logger.warning(
        "Validation error | %s %s | %d field(s) invalid",
        request.method,
        request.url.path,
        len(errors),
    )
    formatted_errors = [
        {
            "field": " -> ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in errors
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed.",
            "error_code": "VALIDATION_ERROR",
            "errors": formatted_errors,
            "request_id": getattr(request.state, "request_id", str(uuid4())),
        },
    )


async def authentication_error_handler(
    request: Request, exc: AuthenticationError
) -> JSONResponse:
    """Map AuthenticationError → 401 Unauthorized."""
    logger.warning("Auth error | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_401_UNAUTHORIZED, exc.message, "UNAUTHORIZED")


async def permission_denied_handler(
    request: Request, exc: PermissionDeniedError
) -> JSONResponse:
    """Map PermissionDeniedError → 403 Forbidden."""
    logger.warning("Permission denied | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_403_FORBIDDEN, exc.message, "FORBIDDEN")


async def user_not_found_handler(request: Request, exc: UserNotFoundError) -> JSONResponse:
    """Map UserNotFoundError → 404 Not Found."""
    logger.warning("User not found | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_404_NOT_FOUND, exc.message, "NOT_FOUND")


async def user_already_exists_handler(
    request: Request, exc: UserAlreadyExistsError
) -> JSONResponse:
    """Map UserAlreadyExistsError → 409 Conflict."""
    logger.warning("User already exists | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_409_CONFLICT, exc.message, "CONFLICT")


async def user_inactive_handler(request: Request, exc: UserInactiveError) -> JSONResponse:
    """Map UserInactiveError → 403 Forbidden."""
    logger.warning("User inactive | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(
        request, status.HTTP_403_FORBIDDEN, exc.message, "ACCOUNT_INACTIVE"
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected exceptions. Hides internal details in production."""
    logger.exception(
        "Unhandled exception | %s %s", request.method, request.url.path, exc_info=True
    )
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected internal error occurred. Please try again later.",
        "INTERNAL_SERVER_ERROR",
    )


async def camera_not_found_handler(request: Request, exc: CameraNotFoundError) -> JSONResponse:
    """Map CameraNotFoundError → 404 Not Found."""
    logger.warning("Camera not found | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_404_NOT_FOUND, exc.message, "CAMERA_NOT_FOUND")


async def camera_in_use_handler(request: Request, exc: CameraInUseError) -> JSONResponse:
    """Map CameraInUseError → 409 Conflict."""
    logger.warning("Camera in use | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_409_CONFLICT, exc.message, "CAMERA_IN_USE")


async def segment_not_found_handler(request: Request, exc: SegmentNotFoundError) -> JSONResponse:
    """Map SegmentNotFoundError → 404 Not Found."""
    logger.warning("Segment not found | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_404_NOT_FOUND, exc.message, "SEGMENT_NOT_FOUND")


async def reading_not_found_handler(request: Request, exc: ReadingNotFoundError) -> JSONResponse:
    """Map ReadingNotFoundError → 404 Not Found."""
    logger.warning("Reading not found | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_404_NOT_FOUND, exc.message, "READING_NOT_FOUND")


async def invalid_reading_time_handler(request: Request, exc: InvalidReadingTimeError) -> JSONResponse:
    """Map InvalidReadingTimeError → 422 Unprocessable Entity."""
    logger.warning("Invalid reading time | %s %s | %s", request.method, request.url.path, exc.message)
    return _error_response(request, status.HTTP_422_UNPROCESSABLE_ENTITY, exc.message, "INVALID_READING_TIME")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI app.

    Called once in main.py during app factory setup.
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(AuthenticationError, authentication_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(PermissionDeniedError, permission_denied_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UserNotFoundError, user_not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UserAlreadyExistsError, user_already_exists_handler)  # type: ignore[arg-type]
    app.add_exception_handler(UserInactiveError, user_inactive_handler)  # type: ignore[arg-type]
    # ── Camera exceptions ─────────────────────────────────────────────────────
    app.add_exception_handler(CameraNotFoundError, camera_not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(CameraInUseError, camera_in_use_handler)  # type: ignore[arg-type]
    # ── Segment exceptions ────────────────────────────────────────────────────
    app.add_exception_handler(SegmentNotFoundError, segment_not_found_handler)  # type: ignore[arg-type]
    # ── Reading exceptions ────────────────────────────────────────────────────
    app.add_exception_handler(ReadingNotFoundError, reading_not_found_handler)  # type: ignore[arg-type]
    app.add_exception_handler(InvalidReadingTimeError, invalid_reading_time_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]

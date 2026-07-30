"""
app/dependencies/auth.py

Reusable FastAPI Depends() factories for authentication and authorization.

CRITICAL: This module is the ONLY place where HTTP authentication glue exists.
All routers and future modules consume authentication via Depends() from here.

Extension point for Backend Developer #2:
    from app.dependencies.auth import get_current_user, require_role
    from app.models.user import UserRole

    # Protected route requiring TRAFFIC_CONTROLLER role:
    @router.get(
        "/traffic-data",
        dependencies=[Depends(require_role(UserRole.TRAFFIC_CONTROLLER))]
    )
    async def get_traffic_data(...): ...

    # Route that needs the current user object:
    @router.get("/my-stats")
    async def my_stats(current_user: User = Depends(get_current_user)):
        ...
"""
import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import (
    PermissionDeniedError,
    TokenExpiredError,
    TokenInvalidError,
    UserInactiveError,
    UserNotFoundError,
)
from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.user_service import UserService

logger = get_logger(__name__)

# Bearer token extractor — auto-adds the 🔒 lock icon in Swagger UI
_bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts and validates the JWT Bearer token,
    then loads and returns the corresponding User from the database.

    Raises:
        TokenExpiredError: JWT has expired.
        TokenInvalidError: JWT is malformed or signature is wrong.
        UserNotFoundError: Token is valid but user no longer exists.
        UserInactiveError: User account has been deactivated.

    Usage:
        @router.get("/protected")
        async def protected(user: User = Depends(get_current_user)):
            return {"user_id": str(user.id)}
    """
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        err_msg = str(exc).lower()
        if "expired" in err_msg:
            raise TokenExpiredError() from exc
        raise TokenInvalidError() from exc

    subject: str | None = payload.get("sub")
    if not subject:
        raise TokenInvalidError()

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise TokenInvalidError()

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if user is None:
        logger.warning("Token valid but user not found | sub=%s", subject)
        raise UserNotFoundError(subject)

    if not user.is_active:
        raise UserInactiveError()

    return user


def require_role(*roles: UserRole):
    """
    RBAC dependency factory.

    Returns a FastAPI dependency that raises PermissionDeniedError
    if the current user does not have one of the required roles.

    Usage (in a router):
        # Single role:
        @router.delete(
            "/users/{user_id}",
            dependencies=[Depends(require_role(UserRole.ADMIN))]
        )

        # Multiple allowed roles:
        @router.get(
            "/traffic",
            dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.TRAFFIC_CONTROLLER))]
        )
    """
    async def _role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            role_names = ", ".join(r.value for r in roles)
            logger.warning(
                "Permission denied | user_id=%s | user_role=%s | required_roles=%s",
                current_user.id,
                current_user.role,
                role_names,
            )
            raise PermissionDeniedError(required_role=role_names)
        return current_user

    return _role_checker


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """FastAPI dependency for AuthService."""
    return AuthService(UserRepository(db))


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """FastAPI dependency for UserService."""
    return UserService(UserRepository(db))

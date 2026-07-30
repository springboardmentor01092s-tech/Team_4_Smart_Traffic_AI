"""
app/routers/auth.py

HTTP routes for authentication endpoints.
Thin layer — delegates all business logic to services.

Routes:
    POST /api/v1/auth/register  — Register a new account
    POST /api/v1/auth/login     — Login and receive a JWT
    POST /api/v1/auth/logout    — Acknowledge logout (stateless JWT)
"""
from fastapi import APIRouter, Depends, status

from app.dependencies.auth import get_auth_service
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description=(
        "Create a new account with the given credentials. "
        "Returns the created user profile (password excluded). "
        "Defaults all new accounts to the PUBLIC_USER role."
    ),
)
async def register(
    data: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> UserRead:
    user = await service.register(data)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and obtain a JWT access token",
    description=(
        "Authenticate with email and password. "
        "Returns a Bearer JWT access token valid for the configured duration. "
        "Include this token in the `Authorization: Bearer <token>` header for protected routes."
    ),
)
async def login(
    data: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.login(data.email, data.password)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Logout (client-side token discard)",
    description=(
        "Acknowledges a logout request. "
        "Because JWTs are stateless, the server cannot invalidate a token. "
        "The client must discard the token. "
        "Future: integrate a token blacklist (Redis) for forced invalidation."
    ),
)
async def logout() -> LogoutResponse:
    return LogoutResponse(message="Successfully logged out.")

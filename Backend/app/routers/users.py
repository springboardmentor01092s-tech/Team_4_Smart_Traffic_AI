"""
app/routers/users.py

HTTP routes for User Management (authenticated users only).

Routes:
    GET /api/v1/users/me  — Get current user profile
    PUT /api/v1/users/me  — Update current user profile
"""
from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user, get_user_service
from app.models.user import User
from app.schemas.user import UserProfile, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current user profile",
    description=(
        "Returns the full profile of the currently authenticated user. "
        "Requires a valid Bearer JWT in the Authorization header."
    ),
)
async def get_me(
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserProfile:
    user = await service.get_profile(current_user)
    return UserProfile.model_validate(user)


@router.put(
    "/me",
    response_model=UserProfile,
    summary="Update current user profile",
    description=(
        "Update mutable profile fields for the authenticated user. "
        "Only `full_name` and `password` can be changed. "
        "All fields are optional — omit any you don't want to change. "
        "Requires a valid Bearer JWT."
    ),
)
async def update_me(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> UserProfile:
    user = await service.update_profile(current_user, data)
    return UserProfile.model_validate(user)

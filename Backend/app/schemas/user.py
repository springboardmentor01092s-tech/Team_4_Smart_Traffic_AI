"""
app/schemas/user.py

Pydantic v2 schemas for User Management endpoints.

Separation of concerns:
  - UserRead: what the API returns (read-only view, NO password)
  - UserProfile: current user's full profile (extended UserRead)
  - UserUpdate: what fields a user may change about themselves
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


class UserRead(BaseModel):
    """
    Public user representation returned by most endpoints.
    Password fields are systematically excluded.
    """

    id: uuid.UUID
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,  # Allow construction from ORM model instances
        "json_schema_extra": {"example": {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "full_name": "Jane Doe",
            "email": "jane.doe@example.com",
            "role": "PUBLIC_USER",
            "is_active": True,
            "is_verified": False,
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:00:00Z",
        }},
    }


class UserProfile(UserRead):
    """
    Extended profile returned by GET /api/v1/users/me.
    Inherits all UserRead fields (add profile-specific fields here later
    without touching UserRead).
    """

    pass


class UserUpdate(BaseModel):
    """
    Request body for PUT /api/v1/users/me.
    All fields are optional — only provided fields are updated.
    """

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=255,
        examples=["Jane Smith"],
        description="Updated display name.",
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        examples=["NewStr0ng!Pass"],
        description="New password. Must be 8–128 characters.",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str | None) -> str | None:
        if v is None:
            return v
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one digit.")
        return v

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str | None) -> str | None:
        return v.strip() if v else v

    model_config = {
        "json_schema_extra": {"example": {
            "full_name": "Jane Smith",
            "password": "NewStr0ng1Pass",
        }},
    }

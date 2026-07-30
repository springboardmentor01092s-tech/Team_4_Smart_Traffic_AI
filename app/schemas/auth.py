"""
app/schemas/auth.py

Pydantic v2 schemas for Authentication endpoints.

These schemas define the exact shape of HTTP request bodies and responses
for /api/v1/auth/* endpoints. They are intentionally decoupled from ORM models.

Validation rules are enforced by Pydantic before the request reaches any
service or repository layer.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Request body for POST /api/v1/auth/register."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        examples=["Jane Doe"],
        description="User's full display name.",
    )
    email: EmailStr = Field(
        ...,
        examples=["jane.doe@example.com"],
        description="Unique email address for login.",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["Str0ng!Password"],
        description="Plain-text password. Must be 8–128 characters.",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Ensure password contains at least one digit and one letter."""
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not (has_letter and has_digit):
            raise ValueError("Password must contain at least one letter and one digit.")
        return v

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        return v.strip()

    model_config = {"json_schema_extra": {"example": {
        "full_name": "Jane Doe",
        "email": "jane.doe@example.com",
        "password": "Str0ng1Pass",
    }}}


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login."""

    email: EmailStr = Field(..., examples=["jane.doe@example.com"])
    password: str = Field(..., min_length=1, max_length=128, examples=["Str0ng1Pass"])

    model_config = {"json_schema_extra": {"example": {
        "email": "jane.doe@example.com",
        "password": "Str0ng1Pass",
    }}}


class TokenResponse(BaseModel):
    """
    Response body for successful login.

    The client must store `access_token` and include it as:
        Authorization: Bearer <access_token>
    in all subsequent protected requests.
    """

    access_token: str = Field(..., description="Signed JWT access token.")
    token_type: str = Field(default="bearer", description="Always 'bearer'.")
    expires_in: int = Field(..., description="Token lifetime in seconds.")

    model_config = {"json_schema_extra": {"example": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 1800,
    }}}


class LogoutResponse(BaseModel):
    """Response body for POST /api/v1/auth/logout."""

    message: str = Field(default="Successfully logged out.")

    model_config = {"json_schema_extra": {"example": {"message": "Successfully logged out."}}}

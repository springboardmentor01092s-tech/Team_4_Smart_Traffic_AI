"""
app/models/user.py

SQLAlchemy 2.x ORM model for the User entity.

This is the ONLY model owned by Backend Developer #1.
Backend Developer #2 must import UserRole and User for FK references
but must NOT modify this file.

Fields:
    id              UUID primary key (server-generated)
    full_name       Display name
    email           Unique login identifier
    hashed_password bcrypt hash — never store plain text
    role            UserRole enum (ADMIN | TRAFFIC_CONTROLLER | PUBLIC_USER)
    is_active       Soft-disable accounts without deleting them
    is_verified     Email verification flag (future feature hook)
    created_at      UTC timestamp, set on INSERT
    updated_at      UTC timestamp, updated on UPDATE
"""
import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, Enum):
    """
    Role-Based Access Control roles.

    Inherits from str so that Pydantic and JSON serialization work
    without extra conversion — the value IS the string representation.

    ADMIN:              Full system access. Can manage users.
    TRAFFIC_CONTROLLER: Can view/manage traffic data and alerts.
    PUBLIC_USER:        Read-only access to public traffic information.
    """

    ADMIN = "ADMIN"
    TRAFFIC_CONTROLLER = "TRAFFIC_CONTROLLER"
    PUBLIC_USER = "PUBLIC_USER"


class User(Base):
    """ORM model representing an authenticated user of the system."""

    __tablename__ = "users"

    # ─── Primary Key ─────────────────────────────────────────────────────────
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Universally unique identifier for the user.",
    )

    # ─── Identity ────────────────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User's display name.",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        doc="Unique email address used for login.",
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="bcrypt hash of the user's password. Never store plain text.",
    )

    # ─── Access Control ──────────────────────────────────────────────────────
    role: Mapped[UserRole] = mapped_column(
        String(50),
        nullable=False,
        default=UserRole.PUBLIC_USER,
        doc="User's RBAC role. Controls what resources they can access.",
    )

    # ─── Status Flags ────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="False when account is suspended. Active by default.",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="True once email has been verified. Hook for future email flow.",
    )

    # ─── Timestamps ──────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        doc="UTC timestamp of account creation.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        doc="UTC timestamp of the most recent update.",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"

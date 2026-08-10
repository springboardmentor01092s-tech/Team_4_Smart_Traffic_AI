"""Create users table

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

This is the initial migration for the TrafficVision AI authentication system.
It creates the `users` table — the ONLY table owned by Backend Developer #1.

Backend Developer #2: Do NOT modify this migration.
Create your own migration files for new tables:
    alembic revision --autogenerate -m "add_traffic_cameras_table"
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the users table with all required columns, constraints, and indexes."""
    op.create_table(
        "users",
        # ── Primary Key ───────────────────────────────────────────────────────
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Universally unique identifier for the user",
        ),
        # ── Identity ──────────────────────────────────────────────────────────
        sa.Column(
            "full_name",
            sa.String(255),
            nullable=False,
            comment="User display name",
        ),
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="Unique email address used for login",
        ),
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=False,
            comment="bcrypt hash of the user password",
        ),
        # ── Role ──────────────────────────────────────────────────────────────
        sa.Column(
            "role",
            sa.String(50),
            nullable=False,
            server_default="PUBLIC_USER",
            comment="RBAC role: ADMIN | TRAFFIC_CONTROLLER | PUBLIC_USER",
        ),
        # ── Status Flags ──────────────────────────────────────────────────────
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="False when account is suspended",
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="True once email has been verified",
        ),
        # ── Timestamps ────────────────────────────────────────────────────────
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp of account creation",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp of the most recent update",
        ),
    )

    # ── Indexes ───────────────────────────────────────────────────────────────
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── Check Constraints ─────────────────────────────────────────────────────
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role IN ('ADMIN', 'TRAFFIC_CONTROLLER', 'PUBLIC_USER')",
    )


def downgrade() -> None:
    """Drop the users table and all associated objects."""
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

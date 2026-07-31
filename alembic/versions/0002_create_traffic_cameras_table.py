"""Create traffic_cameras table

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31 00:00:00.000000

Creates the `traffic_cameras` table — owned by Backend Developer #2.

Design notes (from Engineering Design Document v2.0):
  - UUID primary key with gen_random_uuid() server-side default.
  - Native PostgreSQL ENUM type `camera_status` created before the table.
  - `deleted_at` column for soft-deletion; indexed separately.
  - CHECK constraints for latitude (-90 to 90) and longitude (-180 to 180).
  - FK delete behaviour: traffic_segments will use ON DELETE RESTRICT so
    cameras can never be physically removed while segments reference them.
    (Physical removal is an offline administrative operation.)

Downgrade order:
  1. Drop indexes.
  2. Drop the table (which drops the camera_status ENUM column reference).
  3. Drop the camera_status ENUM type.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Native PostgreSQL ENUM definition for camera operational status.
# This type is created once here and referenced by the table column.
# It is dropped during downgrade after the table is dropped.
camera_status_enum = postgresql.ENUM(
    "ACTIVE",
    "INACTIVE",
    "MAINTENANCE",
    "OFFLINE",
    name="camera_status",
)


def upgrade() -> None:
    """Create the camera_status ENUM type and the traffic_cameras table."""

    # ── 1. Create the native ENUM type ────────────────────────────────────────
    camera_status_enum.create(op.get_bind(), checkfirst=True)

    # ── 2. Create the table ───────────────────────────────────────────────────
    op.create_table(
        "traffic_cameras",
        # ── Primary Key ───────────────────────────────────────────────────────
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Universally unique identifier for the camera",
        ),
        # ── Identity ──────────────────────────────────────────────────────────
        sa.Column(
            "name",
            sa.String(100),
            nullable=False,
            comment="Human-readable camera label (2–100 chars)",
        ),
        sa.Column(
            "location_name",
            sa.String(255),
            nullable=False,
            comment="Textual description of the installation location (2–255 chars)",
        ),
        # ── Geographic Position ───────────────────────────────────────────────
        sa.Column(
            "latitude",
            sa.Double(),
            nullable=False,
            comment="Geographic latitude of the camera. Must be between -90.0 and 90.0",
        ),
        sa.Column(
            "longitude",
            sa.Double(),
            nullable=False,
            comment="Geographic longitude of the camera. Must be between -180.0 and 180.0",
        ),
        # ── Status (native ENUM) ──────────────────────────────────────────────
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "INACTIVE",
                "MAINTENANCE",
                "OFFLINE",
                name="camera_status",
                create_type=False,  # Already created above
            ),
            nullable=False,
            server_default="ACTIVE",
            comment="Operational status of the camera",
        ),
        # ── Optional Details ──────────────────────────────────────────────────
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Optional free-text notes about the camera (max 500 chars)",
        ),
        # ── Timestamps ────────────────────────────────────────────────────────
        sa.Column(
            "installed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp of when the camera was physically installed",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp of record creation",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="UTC timestamp of the most recent update",
        ),
        # ── Soft Delete ───────────────────────────────────────────────────────
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Soft-delete timestamp. NULL = active. Non-NULL = logically deleted.",
        ),
    )

    # ── 3. Indexes ────────────────────────────────────────────────────────────
    op.create_index("ix_traffic_cameras_status", "traffic_cameras", ["status"])
    op.create_index("ix_traffic_cameras_deleted_at", "traffic_cameras", ["deleted_at"])

    # ── 4. Check Constraints ──────────────────────────────────────────────────
    op.create_check_constraint(
        "ck_cameras_latitude",
        "traffic_cameras",
        "latitude BETWEEN -90 AND 90",
    )
    op.create_check_constraint(
        "ck_cameras_longitude",
        "traffic_cameras",
        "longitude BETWEEN -180 AND 180",
    )


def downgrade() -> None:
    """Drop indexes, check constraints, the traffic_cameras table, and the ENUM type."""

    # ── 1. Drop check constraints ─────────────────────────────────────────────
    op.drop_constraint("ck_cameras_longitude", "traffic_cameras", type_="check")
    op.drop_constraint("ck_cameras_latitude", "traffic_cameras", type_="check")

    # ── 2. Drop indexes ───────────────────────────────────────────────────────
    op.drop_index("ix_traffic_cameras_deleted_at", table_name="traffic_cameras")
    op.drop_index("ix_traffic_cameras_status", table_name="traffic_cameras")

    # ── 3. Drop the table ─────────────────────────────────────────────────────
    op.drop_table("traffic_cameras")

    # ── 4. Drop the ENUM type ─────────────────────────────────────────────────
    camera_status_enum.drop(op.get_bind(), checkfirst=True)

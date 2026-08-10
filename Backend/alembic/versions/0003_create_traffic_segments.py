"""Create traffic_segments table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-31 01:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


segment_status_enum = postgresql.ENUM(
    "ACTIVE",
    "INACTIVE",
    "UNDER_MAINTENANCE",
    "CLOSED",
    name="segment_status",
)

congestion_level_enum = postgresql.ENUM(
    "FREE_FLOW",
    "LIGHT",
    "MODERATE",
    "HEAVY",
    "STANDSTILL",
    name="congestion_level",
)


def upgrade() -> None:
    segment_status_enum.create(op.get_bind(), checkfirst=True)
    congestion_level_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "traffic_segments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("start_point", sa.String(255), nullable=False),
        sa.Column("end_point", sa.String(255), nullable=False),
        sa.Column("start_latitude", sa.Double(), nullable=False),
        sa.Column("start_longitude", sa.Double(), nullable=False),
        sa.Column("end_latitude", sa.Double(), nullable=False),
        sa.Column("end_longitude", sa.Double(), nullable=False),
        sa.Column("length_km", sa.Double(), nullable=False),
        sa.Column("speed_limit_kmh", sa.Integer(), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("traffic_cameras.id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "INACTIVE",
                "UNDER_MAINTENANCE",
                "CLOSED",
                name="segment_status",
                create_type=False,
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_traffic_segments_status", "traffic_segments", ["status"])
    op.create_index("ix_traffic_segments_camera_id", "traffic_segments", ["camera_id"])
    op.create_index("ix_traffic_segments_deleted_at", "traffic_segments", ["deleted_at"])

    op.create_check_constraint("ck_segments_length", "traffic_segments", "length_km > 0")
    op.create_check_constraint("ck_segments_speed_limit", "traffic_segments", "speed_limit_kmh BETWEEN 1 AND 300")
    op.create_check_constraint("ck_segments_start_latitude", "traffic_segments", "start_latitude BETWEEN -90 AND 90")
    op.create_check_constraint("ck_segments_start_longitude", "traffic_segments", "start_longitude BETWEEN -180 AND 180")
    op.create_check_constraint("ck_segments_end_latitude", "traffic_segments", "end_latitude BETWEEN -90 AND 90")
    op.create_check_constraint("ck_segments_end_longitude", "traffic_segments", "end_longitude BETWEEN -180 AND 180")


def downgrade() -> None:
    op.drop_constraint("ck_segments_end_longitude", "traffic_segments", type_="check")
    op.drop_constraint("ck_segments_end_latitude", "traffic_segments", type_="check")
    op.drop_constraint("ck_segments_start_longitude", "traffic_segments", type_="check")
    op.drop_constraint("ck_segments_start_latitude", "traffic_segments", type_="check")
    op.drop_constraint("ck_segments_speed_limit", "traffic_segments", type_="check")
    op.drop_constraint("ck_segments_length", "traffic_segments", type_="check")

    op.drop_index("ix_traffic_segments_deleted_at", table_name="traffic_segments")
    op.drop_index("ix_traffic_segments_camera_id", table_name="traffic_segments")
    op.drop_index("ix_traffic_segments_status", table_name="traffic_segments")

    op.drop_table("traffic_segments")

    congestion_level_enum.drop(op.get_bind(), checkfirst=True)
    segment_status_enum.drop(op.get_bind(), checkfirst=True)

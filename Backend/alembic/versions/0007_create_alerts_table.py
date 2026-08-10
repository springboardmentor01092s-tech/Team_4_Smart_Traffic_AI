"""Create alerts table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-31 11:46:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


alert_type_enum = postgresql.ENUM(
    "CONGESTION",
    "ACCIDENT",
    "ROAD_CLOSURE",
    "WEATHER",
    "EMERGENCY",
    "ROADWORKS",
    name="alert_type",
)

alert_severity_enum = postgresql.ENUM(
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
    name="alert_severity",
)

alert_status_enum = postgresql.ENUM(
    "ACTIVE",
    "RESOLVED",
    "DISMISSED",
    name="alert_status",
)


def upgrade() -> None:
    # 1. Create Enums explicitly so they exist before the table
    alert_type_enum.create(op.get_bind(), checkfirst=True)
    alert_severity_enum.create(op.get_bind(), checkfirst=True)
    alert_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create alerts table
    op.create_table(
        "alerts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("traffic_segments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "alert_type",
            postgresql.ENUM(
                "CONGESTION",
                "ACCIDENT",
                "ROAD_CLOSURE",
                "WEATHER",
                "EMERGENCY",
                "ROADWORKS",
                name="alert_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            postgresql.ENUM(
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="alert_severity",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                "ACTIVE",
                "RESOLVED",
                "DISMISSED",
                name="alert_status",
                create_type=False,
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Create Indexes
    op.create_index("ix_alerts_segment_id", "alerts", ["segment_id"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_created_by", "alerts", ["created_by"])
    op.create_index("ix_alerts_created_at", "alerts", [sa.text("created_at DESC")])
    op.create_index("ix_alerts_deleted_at", "alerts", ["deleted_at"])


def downgrade() -> None:
    # 1. Drop Indexes
    op.drop_index("ix_alerts_deleted_at", table_name="alerts")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_index("ix_alerts_created_by", table_name="alerts")
    op.drop_index("ix_alerts_severity", table_name="alerts")
    op.drop_index("ix_alerts_status", table_name="alerts")
    op.drop_index("ix_alerts_segment_id", table_name="alerts")

    # 2. Drop Table
    op.drop_table("alerts")

    # 3. Drop Enums
    alert_status_enum.drop(op.get_bind(), checkfirst=True)
    alert_severity_enum.drop(op.get_bind(), checkfirst=True)
    alert_type_enum.drop(op.get_bind(), checkfirst=True)

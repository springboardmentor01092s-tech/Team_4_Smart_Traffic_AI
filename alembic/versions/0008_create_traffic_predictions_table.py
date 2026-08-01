"""Create traffic predictions table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-31 15:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


prediction_status_enum = postgresql.ENUM(
    "PENDING",
    "COMPLETED",
    "FAILED",
    name="prediction_status",
)


def upgrade() -> None:
    # 1. Create Enums explicitly so they exist before the table
    prediction_status_enum.create(op.get_bind(), checkfirst=True)
    # Note: congestion_level is not created here as it was created in migration 0003

    # 2. Create traffic_predictions table
    op.create_table(
        "traffic_predictions",
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
            "predicted_congestion_level",
            postgresql.ENUM(
                "FREE_FLOW",
                "LIGHT",
                "MODERATE",
                "HEAVY",
                "STANDSTILL",
                name="congestion_level",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("predicted_vehicle_count", sa.Integer(), nullable=True),
        sa.Column("predicted_avg_speed_kmh", sa.Float(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("prediction_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("horizon_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "PENDING",
                "COMPLETED",
                "FAILED",
                name="prediction_status",
                create_type=False,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("confidence_score >= 0.0 AND confidence_score <= 1.0", name="ck_predictions_confidence"),
        sa.CheckConstraint("horizon_minutes > 0", name="ck_predictions_horizon"),
    )

    # 3. Create Indexes
    op.create_index("ix_predictions_segment_id", "traffic_predictions", ["segment_id"])
    op.create_index("ix_predictions_status", "traffic_predictions", ["status"])
    op.create_index("ix_predictions_prediction_for", "traffic_predictions", ["prediction_for"])
    op.create_index("ix_predictions_segment_for", "traffic_predictions", ["segment_id", "prediction_for"])
    op.create_index("ix_predictions_deleted_at", "traffic_predictions", ["deleted_at"])


def downgrade() -> None:
    # 1. Drop Indexes
    op.drop_index("ix_predictions_deleted_at", table_name="traffic_predictions")
    op.drop_index("ix_predictions_segment_for", table_name="traffic_predictions")
    op.drop_index("ix_predictions_prediction_for", table_name="traffic_predictions")
    op.drop_index("ix_predictions_status", table_name="traffic_predictions")
    op.drop_index("ix_predictions_segment_id", table_name="traffic_predictions")

    # 2. Drop Table
    op.drop_table("traffic_predictions")

    # 3. Drop Enum (but not congestion_level!)
    prediction_status_enum.drop(op.get_bind(), checkfirst=True)

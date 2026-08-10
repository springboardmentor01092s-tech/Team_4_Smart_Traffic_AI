"""Create routes table

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-01 05:17:00.000000

Inserts into the migration chain between 0004 (traffic_readings) and the
existing 0007 (alerts). After applying this migration, 0006 creates the
route_segments table.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "routes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("origin_name", sa.String(255), nullable=False),
        sa.Column("destination_name", sa.String(255), nullable=False),
        sa.Column("total_distance_km", sa.Float(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("total_distance_km > 0", name="ck_routes_distance"),
    )

    op.create_index("ix_routes_is_active", "routes", ["is_active"])
    op.create_index("ix_routes_deleted_at", "routes", ["deleted_at"])
    op.create_index("ix_routes_created_at", "routes", [sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_routes_created_at", table_name="routes")
    op.drop_index("ix_routes_deleted_at", table_name="routes")
    op.drop_index("ix_routes_is_active", table_name="routes")
    op.drop_table("routes")

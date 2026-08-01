"""Create route_segments table

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-01 05:17:00.000000

Creates the route_segments join table linking routes to traffic_segments.
FK ondelete behavior:
  - route_id   → ON DELETE CASCADE  (join row removed when route is purged)
  - segment_id → ON DELETE RESTRICT (cannot delete a segment in active use by a route)

Unique constraint on (route_id, sequence_order) is enforced at both the DB
level (via this migration) and at the service layer (pre-flight check).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "route_segments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "route_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("routes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("traffic_segments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("sequence_order >= 1", name="ck_route_segments_order"),
        sa.UniqueConstraint("route_id", "sequence_order", name="uq_route_segment_order"),
    )

    op.create_index("ix_route_segments_route_id", "route_segments", ["route_id"])
    op.create_index("ix_route_segments_segment_id", "route_segments", ["segment_id"])


def downgrade() -> None:
    op.drop_index("ix_route_segments_segment_id", table_name="route_segments")
    op.drop_index("ix_route_segments_route_id", table_name="route_segments")
    op.drop_table("route_segments")

"""create traffic readings table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31 10:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'traffic_readings',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('segment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('vehicle_count', sa.Integer(), nullable=False),
        sa.Column('average_speed_kmh', sa.Float(), nullable=False),
        sa.Column(
            'congestion_level',
            postgresql.ENUM('FREE_FLOW', 'LIGHT', 'MODERATE', 'HEAVY', 'STANDSTILL', name='congestion_level', create_type=False),
            nullable=False
        ),
        sa.Column('occupancy_percent', sa.Float(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('vehicle_count >= 0', name='ck_readings_vehicle_count'),
        sa.CheckConstraint('average_speed_kmh >= 0', name='ck_readings_speed'),
        sa.CheckConstraint('occupancy_percent >= 0 AND occupancy_percent <= 100', name='ck_readings_occupancy'),
        sa.ForeignKeyConstraint(['segment_id'], ['traffic_segments.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_traffic_readings_segment_id', 'traffic_readings', ['segment_id'], unique=False)
    op.create_index('ix_traffic_readings_recorded_at', 'traffic_readings', [sa.text('recorded_at DESC')], unique=False)
    op.create_index('ix_traffic_readings_segment_recorded', 'traffic_readings', ['segment_id', sa.text('recorded_at DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('ix_traffic_readings_segment_recorded', table_name='traffic_readings')
    op.drop_index('ix_traffic_readings_recorded_at', table_name='traffic_readings')
    op.drop_index('ix_traffic_readings_segment_id', table_name='traffic_readings')
    op.drop_table('traffic_readings')

"""Milestone 4 performance indexes and uniqueness constraints

Revision ID: 0009
Revises: 3b8c7d3f099c
Create Date: 2026-08-26 19:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, None] = '3b8c7d3f099c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Notification uniqueness constraint for deduplication & race prevention
    op.create_unique_constraint(
        'uq_notifications_recipient_alert',
        'notifications',
        ['recipient_user_id', 'alert_id'],
    )

    # 2. Composite index on notifications for fast user notification feed queries (recipient + time)
    op.create_index(
        'ix_notifications_user_created',
        'notifications',
        ['recipient_user_id', sa.text('created_at DESC')],
        unique=False,
    )

    # 3. Index on notification status for lifecycle tracking
    op.create_index(
        'ix_notifications_status',
        'notifications',
        ['status'],
        unique=False,
    )

    # 4. Composite index on alerts for frequent segment + status filtering
    op.create_index(
        'ix_alerts_segment_status',
        'alerts',
        ['segment_id', 'status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_alerts_segment_status', table_name='alerts')
    op.drop_index('ix_notifications_status', table_name='notifications')
    op.drop_index('ix_notifications_user_created', table_name='notifications')
    op.drop_constraint('uq_notifications_recipient_alert', 'notifications', type_='unique')

"""Change video_hash unique constraint to per-user

Revision ID: f1673e6f9d52
Revises: 6aff89fb1214
Create Date: 2026-01-17 13:25:18.198288

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1673e6f9d52'
down_revision: Union[str, None] = '6aff89fb1214'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the global unique constraint on video_hash
    op.drop_constraint('lifelog_entries_video_hash_key', 'lifelog_entries', type_='unique')

    # Drop the unique index on video_hash
    op.drop_index('ix_lifelog_entries_video_hash', table_name='lifelog_entries')

    # Create a non-unique index on video_hash for performance
    op.create_index('ix_lifelog_entries_video_hash', 'lifelog_entries', ['video_hash'], unique=False)

    # Add composite unique constraint on (user_id, video_hash)
    op.create_unique_constraint('uix_user_video_hash', 'lifelog_entries', ['user_id', 'video_hash'])


def downgrade() -> None:
    # Remove composite unique constraint
    op.drop_constraint('uix_user_video_hash', 'lifelog_entries', type_='unique')

    # Drop the non-unique index
    op.drop_index('ix_lifelog_entries_video_hash', table_name='lifelog_entries')

    # Restore the unique index and constraint on video_hash
    op.create_index('ix_lifelog_entries_video_hash', 'lifelog_entries', ['video_hash'], unique=True)
    op.create_unique_constraint('lifelog_entries_video_hash_key', 'lifelog_entries', ['video_hash'])

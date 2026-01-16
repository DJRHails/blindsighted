"""Add User and LifelogEntry models for lifelog sync

Revision ID: 604e0a843889
Revises: e4e6f88cabb0
Create Date: 2026-01-16 01:48:56.104171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '604e0a843889'
down_revision: Union[str, None] = 'e4e6f88cabb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('device_identifier', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_identifier')
    )
    op.create_index(op.f('ix_users_device_identifier'), 'users', ['device_identifier'], unique=True)

    # Create lifelog_entries table
    op.create_table(
        'lifelog_entries',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('video_hash', sa.String(length=64), nullable=False),
        sa.Column('r2_key', sa.String(length=512), nullable=False),
        sa.Column('r2_url', sa.String(length=512), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_hash'),
        sa.UniqueConstraint('r2_key')
    )
    op.create_index(op.f('ix_lifelog_entries_user_id'), 'lifelog_entries', ['user_id'], unique=False)
    op.create_index(op.f('ix_lifelog_entries_video_hash'), 'lifelog_entries', ['video_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_lifelog_entries_video_hash'), table_name='lifelog_entries')
    op.drop_index(op.f('ix_lifelog_entries_user_id'), table_name='lifelog_entries')
    op.drop_table('lifelog_entries')
    op.drop_index(op.f('ix_users_device_identifier'), table_name='users')
    op.drop_table('users')

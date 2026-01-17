"""Rename r2 fields to storage fields in files table

Revision ID: bf9373a6baa1
Revises: 6ce552ddfa11
Create Date: 2026-01-17 13:38:15.920924

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf9373a6baa1'
down_revision: Union[str, None] = '6ce552ddfa11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename r2_key to storage_key
    op.alter_column('files', 'r2_key', new_column_name='storage_key')

    # Rename r2_url to storage_url
    op.alter_column('files', 'r2_url', new_column_name='storage_url')


def downgrade() -> None:
    # Rename storage_key back to r2_key
    op.alter_column('files', 'storage_key', new_column_name='r2_key')

    # Rename storage_url back to r2_url
    op.alter_column('files', 'storage_url', new_column_name='r2_url')

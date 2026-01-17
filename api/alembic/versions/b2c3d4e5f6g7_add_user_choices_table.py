"""Add UserChoice model for storing user item selections

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_choices table
    op.create_table(
        'user_choices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_name', sa.String(length=255), nullable=False),
        sa.Column('item_location', sa.String(length=255), nullable=True),
        sa.Column('csv_file_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['csv_file_id'], ['csv_files.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('user_choices')

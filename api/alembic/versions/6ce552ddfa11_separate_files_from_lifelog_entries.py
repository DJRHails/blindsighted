"""Separate files from lifelog entries

Revision ID: 6ce552ddfa11
Revises: f1673e6f9d52
Create Date: 2026-01-17 13:28:54.677499

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '6ce552ddfa11'
down_revision: Union[str, None] = 'f1673e6f9d52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create files table
    op.create_table(
        'files',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('storage_url', sa.String(length=512), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('content_hash'),
        sa.UniqueConstraint('storage_key')
    )
    op.create_index('ix_files_content_hash', 'files', ['content_hash'], unique=True)

    # Step 2: Add file_id column to lifelog_entries (nullable for now)
    op.add_column('lifelog_entries', sa.Column('file_id', sa.UUID(), nullable=True))

    # Step 3: Migrate data - create file entries from unique video_hashes
    # This SQL creates a file for each unique video_hash and updates lifelog_entries
    op.execute("""
        -- Insert unique files from lifelog_entries
        INSERT INTO files (id, content_hash, content_type, storage_key, storage_url, file_size_bytes, duration_seconds, created_at)
        SELECT
            gen_random_uuid() as id,
            video_hash as content_hash,
            'video/mp4' as content_type,
            MIN(r2_key) as storage_key,  -- Take first storage_key for this hash
            MIN(r2_url) as storage_url,  -- Take first storage_url for this hash
            MIN(file_size_bytes) as file_size_bytes,
            MIN(duration_seconds) as duration_seconds,
            MIN(created_at) as created_at
        FROM lifelog_entries
        GROUP BY video_hash;

        -- Update lifelog_entries to reference files
        UPDATE lifelog_entries le
        SET file_id = f.id
        FROM files f
        WHERE le.video_hash = f.content_hash;
    """)

    # Step 4: Make file_id NOT NULL now that all entries have been migrated
    op.alter_column('lifelog_entries', 'file_id', nullable=False)

    # Step 5: Add foreign key constraint
    op.create_foreign_key(
        'lifelog_entries_file_id_fkey',
        'lifelog_entries',
        'files',
        ['file_id'],
        ['id']
    )
    op.create_index('ix_lifelog_entries_file_id', 'lifelog_entries', ['file_id'])

    # Step 6: Drop old constraint
    op.drop_constraint('uix_user_video_hash', 'lifelog_entries', type_='unique')

    # Step 7: Add new constraint (user_id, file_id must be unique)
    op.create_unique_constraint('uix_user_file', 'lifelog_entries', ['user_id', 'file_id'])

    # Step 8: Drop old columns from lifelog_entries
    op.drop_index('ix_lifelog_entries_video_hash', table_name='lifelog_entries')
    op.drop_column('lifelog_entries', 'video_hash')
    op.drop_column('lifelog_entries', 'r2_key')
    op.drop_column('lifelog_entries', 'r2_url')
    op.drop_column('lifelog_entries', 'file_size_bytes')
    op.drop_column('lifelog_entries', 'duration_seconds')


def downgrade() -> None:
    # Step 1: Add back old columns to lifelog_entries
    op.add_column('lifelog_entries', sa.Column('duration_seconds', sa.Float(), nullable=True))
    op.add_column('lifelog_entries', sa.Column('file_size_bytes', sa.Integer(), nullable=True))
    op.add_column('lifelog_entries', sa.Column('r2_url', sa.String(512), nullable=True))
    op.add_column('lifelog_entries', sa.Column('r2_key', sa.String(512), nullable=True))
    op.add_column('lifelog_entries', sa.Column('video_hash', sa.String(64), nullable=True))

    # Step 2: Migrate data back from files to lifelog_entries
    op.execute("""
        UPDATE lifelog_entries le
        SET
            video_hash = f.content_hash,
            r2_key = f.storage_key,
            r2_url = f.storage_url,
            file_size_bytes = f.file_size_bytes,
            duration_seconds = f.duration_seconds
        FROM files f
        WHERE le.file_id = f.id;
    """)

    # Step 3: Make columns NOT NULL
    op.alter_column('lifelog_entries', 'video_hash', nullable=False)
    op.alter_column('lifelog_entries', 'r2_key', nullable=False)
    op.alter_column('lifelog_entries', 'r2_url', nullable=False)
    op.alter_column('lifelog_entries', 'file_size_bytes', nullable=False)
    op.alter_column('lifelog_entries', 'duration_seconds', nullable=False)

    # Step 4: Drop new constraint
    op.drop_constraint('uix_user_file', 'lifelog_entries', type_='unique')

    # Step 5: Add back old constraint
    op.create_unique_constraint('uix_user_video_hash', 'lifelog_entries', ['user_id', 'video_hash'])
    op.create_index('ix_lifelog_entries_video_hash', 'lifelog_entries', ['video_hash'])

    # Step 6: Drop foreign key and file_id column
    op.drop_index('ix_lifelog_entries_file_id', table_name='lifelog_entries')
    op.drop_constraint('lifelog_entries_file_id_fkey', 'lifelog_entries', type_='foreignkey')
    op.drop_column('lifelog_entries', 'file_id')

    # Step 7: Drop files table
    op.drop_index('ix_files_content_hash', table_name='files')
    op.drop_table('files')

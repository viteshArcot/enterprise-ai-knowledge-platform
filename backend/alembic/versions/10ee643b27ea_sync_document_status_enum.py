"""Synchronize document_status enum with the application."""

from typing import Sequence, Union

from alembic import op


revision: str = "10ee643b27ea"
down_revision: Union[str, Sequence[str], None] = "5211797a1770"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add all DocumentStatus values required by the application."""
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'document_status'
                  AND e.enumlabel = 'UPLOADING'
            ) THEN
                ALTER TYPE document_status ADD VALUE 'UPLOADING';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'document_status'
                  AND e.enumlabel = 'PROCESSING'
            ) THEN
                ALTER TYPE document_status ADD VALUE 'PROCESSING';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'document_status'
                  AND e.enumlabel = 'READY'
            ) THEN
                ALTER TYPE document_status ADD VALUE 'READY';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_enum e
                JOIN pg_type t ON t.oid = e.enumtypid
                WHERE t.typname = 'document_status'
                  AND e.enumlabel = 'FAILED'
            ) THEN
                ALTER TYPE document_status ADD VALUE 'FAILED';
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """PostgreSQL does not support safely removing enum values in place."""
    pass
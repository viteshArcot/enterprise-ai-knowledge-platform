"""migrate_vector_to_2048_dims

Revision ID: fced49deaebd
Revises: 
Create Date: 2026-08-08 17:47:55.148316

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fced49deaebd'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute('UPDATE chunks SET embedding = NULL;')
    op.execute('ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(2048);')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('UPDATE chunks SET embedding = NULL;')
    op.execute('ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768);')

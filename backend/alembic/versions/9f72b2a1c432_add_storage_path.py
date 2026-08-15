"""Add storage_path to Document

Revision ID: 9f72b2a1c432
Revises: 10ee643b27ea
Create Date: 2026-08-15 15:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f72b2a1c432'
down_revision: Union[str, Sequence[str], None] = '10ee643b27ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('storage_path', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column('documents', 'storage_path')

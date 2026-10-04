"""agent personas: persona dossier column

Revision ID: c968db45ebda
Revises: 0103ddd98e13
Create Date: 2026-10-04 03:30:20.178308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'c968db45ebda'
down_revision: Union[str, None] = '0103ddd98e13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('agents', sa.Column('persona', sa.Text(), nullable=False, server_default=''))

def downgrade() -> None:
    op.drop_column('agents', 'persona')

"""remove_cmd_template_header_template_column

Revision ID: 4056b7c2d2f0
Revises: ebfdcd8bed6d
Create Date: 2026-09-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4056b7c2d2f0'
down_revision: Union[str, Sequence[str], None] = 'ebfdcd8bed6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('cmd_templates') as batch_op:
        batch_op.drop_column('header_template')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('cmd_templates') as batch_op:
        batch_op.add_column(
            sa.Column('header_template', sa.Text(), nullable=True)
        )

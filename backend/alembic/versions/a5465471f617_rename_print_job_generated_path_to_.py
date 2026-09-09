"""rename_print_job_generated_path_to_generated_prefix

Revision ID: a5465471f617
Revises: a0abfa6a2e62
Create Date: 2026-09-09 08:29:08.575801

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5465471f617'
down_revision: Union[str, Sequence[str], None] = 'a0abfa6a2e62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('print_jobs') as batch_op:
        batch_op.alter_column(
            'generated_path',
            new_column_name='generated_prefix',
            existing_type=sa.String(length=255)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('print_jobs') as batch_op:
        batch_op.alter_column(
            'generated_prefix',
            new_column_name='generated_path',
            existing_type=sa.String(length=255)
        )

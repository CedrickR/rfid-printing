"""rename_print_job_generated_file_to_generated_path

Revision ID: a0abfa6a2e62
Revises: 6c7b0d0920f5
Create Date: 2026-09-08 11:14:00.430593

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0abfa6a2e62'
down_revision: Union[str, Sequence[str], None] = '6c7b0d0920f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('print_jobs') as batch_op:
        batch_op.alter_column(
            'generated_file',
            new_column_name='generated_path',
            existing_type=sa.String(length=255)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('print_jobs') as batch_op:
        batch_op.alter_column(
            'generated_path',
            new_column_name='generated_file',
            existing_type=sa.String(length=255)
        )

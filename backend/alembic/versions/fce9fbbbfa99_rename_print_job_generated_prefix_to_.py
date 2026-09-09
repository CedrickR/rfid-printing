"""rename_print_job_generated_prefix_to_generated_files

Revision ID: fce9fbbbfa99
Revises: 7e1feba0fbfc
Create Date: 2026-09-09 13:11:31.027796

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fce9fbbbfa99'
down_revision: Union[str, Sequence[str], None] = '7e1feba0fbfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('print_jobs') as batch_op:
        batch_op.alter_column(
            'generated_prefix',
            new_column_name='generated_files',
            type_=sa.Text(),
            existing_type=sa.String(length=255)
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('print_jobs') as batch_op:
        batch_op.alter_column(
            'generated_files',
            new_column_name='generated_prefix',
            type_=sa.String(length=255),
            existing_type=sa.Text()
        )

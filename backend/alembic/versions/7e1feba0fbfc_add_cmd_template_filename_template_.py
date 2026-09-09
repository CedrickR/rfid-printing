"""add_cmd_template_filename_template_column

Revision ID: 7e1feba0fbfc
Revises: a5465471f617
Create Date: 2026-09-09 13:11:23.125513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7e1feba0fbfc'
down_revision: Union[str, Sequence[str], None] = 'a5465471f617'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_FILENAME_TEMPLATE = "print_job_{{JobId}}_{{BienId}}"


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('cmd_templates') as batch_op:
        batch_op.add_column(
            sa.Column('filename_template', sa.Text(), nullable=True)
        )

    cmd_templates = sa.table(
        'cmd_templates',
        sa.column('filename_template', sa.Text())
    )
    op.execute(
        cmd_templates.update()
        .where(cmd_templates.c.filename_template.is_(None))
        .values(filename_template=DEFAULT_FILENAME_TEMPLATE)
    )

    with op.batch_alter_table('cmd_templates') as batch_op:
        batch_op.alter_column(
            'filename_template',
            existing_type=sa.Text(),
            nullable=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('cmd_templates') as batch_op:
        batch_op.drop_column('filename_template')

"""add_inventory_check_line_designation_and_bien_id_temporaire

Revision ID: 762b780a94de
Revises: 952fc28c8e95
Create Date: 2026-09-16 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '762b780a94de'
down_revision: Union[str, Sequence[str], None] = '952fc28c8e95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('inventory_check_lines') as batch_op:
        batch_op.add_column(
            sa.Column('designation', sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                'bien_id_temporaire',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false()
            )
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('inventory_check_lines') as batch_op:
        batch_op.drop_column('bien_id_temporaire')
        batch_op.drop_column('designation')

"""add_asset_type_bien_id_column

Revision ID: 47e098fc9a2b
Revises: 1cb319562b41
Create Date: 2026-09-16 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47e098fc9a2b'
down_revision: Union[str, Sequence[str], None] = '1cb319562b41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('assets') as batch_op:
        batch_op.add_column(
            sa.Column('type_bien_id', sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            'fk_assets_type_bien_id_asset_types',
            'asset_types',
            ['type_bien_id'],
            ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('assets') as batch_op:
        batch_op.drop_constraint(
            'fk_assets_type_bien_id_asset_types', type_='foreignkey'
        )
        batch_op.drop_column('type_bien_id')

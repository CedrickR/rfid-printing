"""add_inventory_check_lines_table

Revision ID: 952fc28c8e95
Revises: 47e098fc9a2b
Create Date: 2026-09-16 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '952fc28c8e95'
down_revision: Union[str, Sequence[str], None] = '47e098fc9a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'inventory_check_lines',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('local_libelle', sa.String(length=255), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('bien_id', sa.String(length=100), nullable=True),
        sa.Column('type_bien_id', sa.Integer(), nullable=True),
        sa.Column('commentaire', sa.Text(), nullable=True),
        sa.Column('statut', sa.String(length=20), nullable=False),
        sa.Column('updated_by', sa.String(length=100), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['type_bien_id'], ['asset_types.id']),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        'ix_inventory_check_lines_local_libelle',
        'inventory_check_lines',
        ['local_libelle']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_inventory_check_lines_local_libelle',
        table_name='inventory_check_lines'
    )
    op.drop_table('inventory_check_lines')

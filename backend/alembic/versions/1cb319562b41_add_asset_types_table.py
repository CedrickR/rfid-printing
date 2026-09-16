"""add_asset_types_table

Revision ID: 1cb319562b41
Revises: 4056b7c2d2f0
Create Date: 2026-09-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1cb319562b41'
down_revision: Union[str, Sequence[str], None] = '4056b7c2d2f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_ASSET_TYPES = [
    "Bureau Fauteuil",
    "Caisson",
    "Armoire haute",
    "Armoire basse",
    "Porte-Manteau",
    "Copieur",
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'asset_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('libelle', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('libelle')
    )

    asset_types = sa.table(
        'asset_types',
        sa.column('libelle', sa.String())
    )

    op.bulk_insert(
        asset_types,
        [{"libelle": libelle} for libelle in DEFAULT_ASSET_TYPES]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('asset_types')

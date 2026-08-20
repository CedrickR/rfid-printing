"""restructure_bureau_mappings_columns

Revision ID: 749d6f4769ed
Revises: 8c04d96e73f7
Create Date: 2026-08-20 11:01:54.737813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '749d6f4769ed'
down_revision: Union[str, Sequence[str], None] = '8c04d96e73f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Restructuration complète des colonnes (ancien schéma
    # codelieu/batiment/etage/bureau incompatible avec le nouveau) : les
    # données existantes ne peuvent pas être translittérées
    # automatiquement (pas de valeur pour nombre_poste_prevu). Un
    # réimport du fichier bureaux est nécessaire après cette migration.
    op.execute('DELETE FROM bureau_mappings')

    with op.batch_alter_table('bureau_mappings') as batch_op:
        batch_op.add_column(
            sa.Column('code_piece_service', sa.String(length=100), nullable=False)
        )
        batch_op.add_column(sa.Column('niveau', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('nom_piece', sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column('nombre_poste_prevu', sa.Integer(), nullable=True)
        )
        batch_op.create_unique_constraint(
            'uq_bureau_mappings_code_piece_service', ['code_piece_service']
        )
        batch_op.drop_column('bureau')
        batch_op.drop_column('batiment')
        batch_op.drop_column('codelieu')
        batch_op.drop_column('etage')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute('DELETE FROM bureau_mappings')

    with op.batch_alter_table('bureau_mappings') as batch_op:
        batch_op.add_column(sa.Column('etage', sa.VARCHAR(length=255), nullable=True))
        batch_op.add_column(
            sa.Column('codelieu', sa.VARCHAR(length=100), nullable=False)
        )
        batch_op.add_column(
            sa.Column('batiment', sa.VARCHAR(length=255), nullable=True)
        )
        batch_op.add_column(sa.Column('bureau', sa.VARCHAR(length=255), nullable=True))
        batch_op.create_unique_constraint(
            'uq_bureau_mappings_codelieu', ['codelieu']
        )
        batch_op.drop_constraint(
            'uq_bureau_mappings_code_piece_service', type_='unique'
        )
        batch_op.drop_column('nombre_poste_prevu')
        batch_op.drop_column('nom_piece')
        batch_op.drop_column('niveau')
        batch_op.drop_column('code_piece_service')

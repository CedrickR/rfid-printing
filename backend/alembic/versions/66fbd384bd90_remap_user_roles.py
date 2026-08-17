"""remap_user_roles

Introduit le profil "administrateur" : les comptes existants avec le
rôle "gestionnaire" (jusqu'ici seul rôle à privilèges élevés) migrent
vers "administrateur" pour conserver leurs accès (modèle CMD, gestion
des utilisateurs, réinitialisation de la base). Les comptes "employe"
migrent vers le nouveau rôle restreint "lecteur" ; un administrateur
peut ensuite les promouvoir "gestionnaire" si besoin.

Revision ID: 66fbd384bd90
Revises: 2a75c9448f34
Create Date: 2026-08-17 10:10:43.094211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66fbd384bd90'
down_revision: Union[str, Sequence[str], None] = '2a75c9448f34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    conn = op.get_bind()

    conn.execute(
        sa.text(
            "UPDATE users SET role = 'administrateur' "
            "WHERE role = 'gestionnaire'"
        )
    )

    conn.execute(
        sa.text(
            "UPDATE users SET role = 'lecteur' "
            "WHERE role = 'employe'"
        )
    )


def downgrade() -> None:

    conn = op.get_bind()

    conn.execute(
        sa.text(
            "UPDATE users SET role = 'gestionnaire' "
            "WHERE role = 'administrateur'"
        )
    )

    conn.execute(
        sa.text(
            "UPDATE users SET role = 'employe' "
            "WHERE role = 'lecteur'"
        )
    )

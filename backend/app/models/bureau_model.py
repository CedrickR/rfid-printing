from datetime import datetime
from datetime import UTC

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class BureauImport(Base):
    """
    Historique des imports du fichier CSV de correspondance bureaux
    (colonnes : niveau, nom_piece, code_piece_service,
    nombre_poste_prevu).
    """

    __tablename__ = "bureau_imports"

    id = Column(
        Integer,
        primary_key=True
    )

    filename = Column(
        String(255),
        nullable=False
    )

    imported_by = Column(
        String(100),
        nullable=False
    )

    imported_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    total_rows = Column(
        Integer,
        default=0
    )

    added_count = Column(
        Integer,
        default=0
    )

    updated_count = Column(
        Integer,
        default=0
    )


class BureauMapping(Base):
    """
    Pièce (bureau) connue pour un code pièce, pour affichage dans la
    colonne "Bureau" de l'inventaire (jointure entre
    `code_piece_service` et `Asset.local_numero`) et pour la
    répartition ordinateurs/écrans par bureau du tableau de bord. Un
    seul enregistrement par code_piece_service, mis à jour à chaque
    nouvel import (pas de doublon).
    """

    __tablename__ = "bureau_mappings"

    id = Column(
        Integer,
        primary_key=True
    )

    code_piece_service = Column(
        String(100),
        nullable=False,
        unique=True
    )

    niveau = Column(
        String(255)
    )

    nom_piece = Column(
        String(255)
    )

    nombre_poste_prevu = Column(
        Integer,
        default=0
    )

    import_id = Column(
        Integer,
        ForeignKey("bureau_imports.id"),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

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
    (colonnes : codelieu, batiment, etage, bureau).
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
    Bureau (bâtiment/étage/bureau) connu pour un code lieu, pour
    affichage dans la colonne "Bureau" de l'inventaire (jointure sur
    `Asset.local_numero`). Un seul enregistrement par codelieu, mis à
    jour à chaque nouvel import (pas de doublon).
    """

    __tablename__ = "bureau_mappings"

    id = Column(
        Integer,
        primary_key=True
    )

    codelieu = Column(
        String(100),
        nullable=False,
        unique=True
    )

    batiment = Column(
        String(255)
    )

    etage = Column(
        String(255)
    )

    bureau = Column(
        String(255)
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

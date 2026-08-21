from datetime import datetime
from datetime import UTC

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class GlpiImport(Base):
    """
    Historique des imports d'exports GLPI (un fichier par type de bien :
    ordinateur, moniteur, périphérique, logiciel, imprimante).
    """

    __tablename__ = "glpi_imports"

    id = Column(
        Integer,
        primary_key=True
    )

    glpi_type = Column(
        String(50),
        nullable=False
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


class GlpiAsset(Base):
    """
    Numéro de la pièce (GLPI) connu pour un Bien ID, pour comparaison
    avec le numéro local déjà enregistré dans l'inventaire. Un seul
    enregistrement par bien_id, mis à jour à chaque nouvel import
    (pas de doublon).
    """

    __tablename__ = "glpi_assets"

    id = Column(
        Integer,
        primary_key=True
    )

    bien_id = Column(
        String(100),
        nullable=False,
        unique=True
    )

    numero_piece = Column(
        String(100)
    )

    lieu = Column(
        String(255)
    )

    statut = Column(
        String(100)
    )

    utilisateur = Column(
        String(255)
    )

    numero_serie = Column(
        String(255)
    )

    glpi_type = Column(
        String(50),
        nullable=False
    )

    import_id = Column(
        Integer,
        ForeignKey("glpi_imports.id"),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

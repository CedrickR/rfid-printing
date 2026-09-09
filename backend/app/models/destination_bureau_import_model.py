from datetime import datetime
from datetime import UTC

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class DestinationBureauImport(Base):
    """
    Historique des imports du fichier CSV de mise à jour Destination/
    Bureau (colonnes : numero, Destination, Codes pièces et niveau),
    keyé par Bien ID plutôt que par code pièce (contrairement à
    l'import Bureaux existant).
    """

    __tablename__ = "destination_bureau_imports"

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

    updated_count = Column(
        Integer,
        default=0
    )

    unmatched_count = Column(
        Integer,
        default=0
    )

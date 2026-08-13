from datetime import datetime
from datetime import UTC

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class RfidScanFile(Base):
    """
    Fichier CSV (2 colonnes sans en-tête, ';') issu d'un lecteur RFID :
    colonne 1 = "L261" + numéro du lieu, colonne 2 = "261" + Bien ID.
    """

    __tablename__ = "rfid_scan_files"

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


class RfidScanLine(Base):
    __tablename__ = "rfid_scan_lines"

    id = Column(
        Integer,
        primary_key=True
    )

    scan_file_id = Column(
        Integer,
        ForeignKey("rfid_scan_files.id"),
        nullable=False
    )

    lieu_numero = Column(
        String(50),
        nullable=False
    )

    bien_id = Column(
        String(100),
        nullable=False
    )

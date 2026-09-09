from datetime import datetime
from datetime import UTC

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    created_by = Column(
        String(100),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

    status = Column(
        String(50),
        default="PENDING",
        nullable=False
    )

    labels_count = Column(
        Integer,
        default=0,
        nullable=False
    )

    # Nom du sous-dossier (relatif au dossier "generated/") déposé lors
    # de la génération : contient un fichier .cmd par bien du lot.
    generated_path = Column(
        String(255),
        nullable=True
    )

    generated_at = Column(
        DateTime,
        nullable=True
    )
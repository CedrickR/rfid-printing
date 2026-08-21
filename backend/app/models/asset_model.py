from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(
        Integer,
        primary_key=True
    )

    bien_id = Column(
        String(100),
        nullable=False
    )

    bien_designation = Column(
        String(255),
        nullable=False
    )

    bien_amort_date_sortie = Column(
        String(50)
    )

    local_numero = Column(
        String(100)
    )

    immeuble_libelle = Column(
        String(255)
    )

    niveau_libelle = Column(
        String(255)
    )

    local_libelle = Column(
        String(255)
    )

    destination = Column(
        String(255)
    )

    utilisateur = Column(
        String(255)
    )

    is_active = Column(
        Boolean,
        default=True
    )

    import_id = Column(
        Integer,
        ForeignKey("imports.id"),
        nullable=False
    )
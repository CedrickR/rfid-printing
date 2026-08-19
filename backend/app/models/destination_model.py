from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class Destination(Base):
    """
    Valeur possible de la liste déroulante "Destination" de
    l'inventaire (`Asset.destination`), gérée depuis la page
    d'administration dédiée.
    """

    __tablename__ = "destinations"

    id = Column(
        Integer,
        primary_key=True
    )

    libelle = Column(
        String(255),
        nullable=False,
        unique=True
    )

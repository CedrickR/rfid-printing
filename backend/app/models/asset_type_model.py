from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class AssetType(Base):
    """
    Valeur possible de la liste déroulante "Type de bien" de
    l'inventaire (`Asset.type_bien_id`), gérée depuis la page
    d'administration Destination et Bureau (onglet Types de bien).
    """

    __tablename__ = "asset_types"

    id = Column(
        Integer,
        primary_key=True
    )

    libelle = Column(
        String(255),
        nullable=False,
        unique=True
    )

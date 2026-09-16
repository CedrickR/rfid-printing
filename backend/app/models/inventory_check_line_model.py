from datetime import datetime
from datetime import UTC

from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from app.database import Base


class InventoryCheckLine(Base):
    """
    Ligne du suivi de l'inventaire par local (§2.13) : soit un bien
    actif connu de l'inventaire actuellement affecté à ce local
    (`asset_id` renseigné), soit un bien "en trop" ajouté manuellement
    (`asset_id` NULL, `bien_id`/`designation`/`type_bien_id` alors
    renseignés directement ici).

    Pour une ligne liée à un bien connu, le Bien ID, la désignation et
    le type de bien affichés viennent toujours en direct de l'Asset
    lié (jamais dupliqués ici) : seuls le statut et le commentaire
    sont propres à la ligne.

    Un bien "en trop" dont le Bien ID est inconnu sur le terrain (ex.
    fauteuil non étiqueté) peut être ajouté sans Bien ID : une
    référence temporaire ("SN-<id>") est alors générée et
    `bien_id_temporaire` vaut True, le temps que la ligne soit
    rattachée à son vrai Bien ID (InventoryCheckService.attach_bien_id).
    """

    __tablename__ = "inventory_check_lines"

    id = Column(
        Integer,
        primary_key=True
    )

    local_libelle = Column(
        String(255),
        nullable=False
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.id"),
        nullable=True
    )

    # Renseignés uniquement pour un bien "en trop" (asset_id NULL).
    bien_id = Column(
        String(100)
    )

    bien_id_temporaire = Column(
        Boolean,
        nullable=False,
        default=False
    )

    designation = Column(
        String(255)
    )

    type_bien_id = Column(
        Integer,
        ForeignKey("asset_types.id"),
        nullable=True
    )

    commentaire = Column(
        Text
    )

    statut = Column(
        String(20),
        nullable=False
    )

    updated_by = Column(
        String(100),
        nullable=False
    )

    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False
    )

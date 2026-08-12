from datetime import datetime
from datetime import UTC

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text

from app.database import Base


class CmdTemplate(Base):
    """
    Modèle du fichier .cmd généré pour un lot d'impression. Une seule
    ligne active : la plus récente (id le plus élevé) fait foi.
    """

    __tablename__ = "cmd_templates"

    id = Column(
        Integer,
        primary_key=True
    )

    header_template = Column(
        Text,
        nullable=False
    )

    line_template = Column(
        Text,
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

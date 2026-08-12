from datetime import datetime, UTC

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import DateTime

from app.database import Base


class Import(Base):
    __tablename__ = "imports"

    id = Column(
        Integer,
        primary_key=True,
        index=True
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

    active_assets = Column(
        Integer,
        default=0
    )

    excluded_assets = Column(
        Integer,
        default=0
    )
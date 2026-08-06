from datetime import datetime
from datetime import UTC

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from app.database import Base


class PrintHistory(Base):
    __tablename__ = "print_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    job_id = Column(
        Integer,
        nullable=False
    )

    username = Column(
        String(100),
        nullable=False
    )

    action = Column(
        String(50),
        nullable=False
    )

    file_name = Column(
        String(255)
    )

    labels_count = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC)
    )
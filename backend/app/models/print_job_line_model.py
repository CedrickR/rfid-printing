from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import ForeignKey

from app.database import Base


class PrintJobLine(Base):
    __tablename__ = "print_job_lines"

    id = Column(
        Integer,
        primary_key=True
    )

    job_id = Column(
        Integer,
        ForeignKey("print_jobs.id")
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.id")
    )
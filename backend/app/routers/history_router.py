from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.asset_model import Asset
from app.models.print_history_model import (
    PrintHistory
)
from app.models.print_job_line_model import PrintJobLine

from app.auth import get_current_user

router = APIRouter(
    prefix="/api/history",
    tags=["History"]
)

@router.get("/")
def get_history(
    bien_id: str = Query(default=""),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    query = db.query(PrintHistory)

    if bien_id:

        matching_job_ids = (
            db.query(PrintJobLine.job_id)
            .join(Asset, Asset.id == PrintJobLine.asset_id)
            .filter(Asset.bien_id.contains(bien_id))
            .distinct()
        )

        query = query.filter(
            PrintHistory.job_id.in_(matching_job_ids)
        )

    history = (
        query
        .order_by(
            PrintHistory.created_at.desc()
        )
        .all()
    )

    return history

@router.get("/me")
def get_my_history(
    current_user=Depends(
        get_current_user
    ),
    db: Session = Depends(get_db)
):

    history = (
        db.query(PrintHistory)
        .filter(
            PrintHistory.username
            ==
            current_user["sub"]
        )
        .all()
    )

    return history

@router.get("/{job_id}")
def get_job_history(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    records = (
        db.query(PrintHistory)
        .filter(
            PrintHistory.job_id == job_id
        )
        .all()
    )

    return records
from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.print_history_model import (
    PrintHistory
)

from app.auth import get_current_user

router = APIRouter(
    prefix="/api/history",
    tags=["History"]
)

@router.get("/")
def get_history(
    db: Session = Depends(get_db)
):

    history = (
        db.query(PrintHistory)
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
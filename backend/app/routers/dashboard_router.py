from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.asset_model import Asset
from app.models.print_job_model import PrintJob
from app.models.print_history_model import PrintHistory
from app.models.import_model import Import

from app.auth import get_current_user

router = APIRouter(
    prefix="/api/dashboard",
    tags=["Dashboard"]
)


@router.get("")
def get_dashboard_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    imports_count = (
        db.query(Import)
        .count()
    )

    active_assets = (
        db.query(Asset)
        .filter(
            Asset.is_active == True
        )
        .count()
    )

    jobs_count = (
        db.query(PrintJob)
        .count()
    )

    generated_count = (
        db.query(PrintHistory)
        .filter(
            PrintHistory.action == "GENERATED"
        )
        .count()
    )

    reprints_count = (
        db.query(PrintHistory)
        .filter(
            PrintHistory.action == "REPRINTED"
        )
        .count()
    )

    pending_jobs = (
        db.query(PrintJob)
        .filter(
            PrintJob.status == "PENDING"
        )
        .count()
    )

    return {
        "imports": imports_count,
        "active_assets": active_assets,
        "jobs": jobs_count,
        "generated": generated_count,
        "reprints": reprints_count,
        "pending": pending_jobs
    }

@router.get("/recent")
def get_recent_activity(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    history = (
        db.query(PrintHistory)
        .order_by(
            PrintHistory.id.desc()
        )
        .limit(10)
        .all()
    )
    return [
        {
            "id": item.id,
            "job_id": item.job_id,
            "username": item.username,
            "action": item.action,
            "file_name": item.file_name,
            "labels_count": item.labels_count,
            "created_at": item.created_at
        }
        for item in history
    ]


from datetime import UTC
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.responses import FileResponse

from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db

from app.models.asset_model import Asset
from app.models.print_history_model import PrintHistory
from app.models.print_job_line_model import PrintJobLine
from app.models.print_job_model import PrintJob

from app.schemas import CreatePrintJobRequest

from app.services.cmd_generator import CommandGenerator
from app.services.reprint_service import ReprintService

BASE_DIR = Path(__file__).resolve().parent.parent.parent

router = APIRouter(
    prefix="/api/print",
    tags=["Printing"]
)


@router.post("/jobs")
def create_print_job(
    request: CreatePrintJobRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Création d'un lot d'impression RFID
    """

    if not request.asset_ids:
        raise HTTPException(
            status_code=400,
            detail="Aucun bien sélectionné"
        )

    assets = (
        db.query(Asset)
        .filter(
            Asset.id.in_(request.asset_ids)
        )
        .all()
    )

    if not assets:
        raise HTTPException(
            status_code=404,
            detail="Aucun bien trouvé"
        )

    job = PrintJob(
        created_by=current_user["sub"],
        labels_count=len(assets),
        status="PENDING"
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    for asset in assets:

        line = PrintJobLine(
            job_id=job.id,
            asset_id=asset.id
        )

        db.add(line)

    db.commit()

    return {
        "job_id": job.id,
        "labels_count": job.labels_count,
        "status": job.status
    }


@router.get("/jobs")
def get_jobs(
    db: Session = Depends(get_db)
):
    """
    Liste des lots
    """

    jobs = db.query(PrintJob).all()

    return [
        {
            "id": job.id,
            "created_by": job.created_by,
            "created_at": job.created_at,
            "status": job.status,
            "labels_count": job.labels_count
        }
        for job in jobs
    ]


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Détail d'un lot
    """

    job = (
        db.query(PrintJob)
        .filter(
            PrintJob.id == job_id
        )
        .first()
    )

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

    lines = (
        db.query(PrintJobLine)
        .filter(
            PrintJobLine.job_id == job.id
        )
        .all()
    )

    assets = []

    for line in lines:

        asset = (
            db.query(Asset)
            .filter(
                Asset.id == line.asset_id
            )
            .first()
        )

        if asset:

            assets.append(
                {
                    "id": asset.id,
                    "bien_id": asset.bien_id,
                    "bien_designation": asset.bien_designation,
                    "is_active": asset.is_active
                }
            )

    return {
        "job_id": job.id,
        "created_by": job.created_by,
        "created_at": job.created_at,
        "status": job.status,
        "labels_count": job.labels_count,
        "assets": assets
    }


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Suppression d'un lot
    """

    job = (
        db.query(PrintJob)
        .filter(
            PrintJob.id == job_id
        )
        .first()
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

    (
        db.query(PrintJobLine)
        .filter(
            PrintJobLine.job_id == job.id
        )
        .delete()
    )

    db.delete(job)

    db.commit()

    return {
        "message": "Lot supprimé"
    }


@router.post("/jobs/{job_id}/generate")
def generate_print_job_file(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Génération du fichier CMD
    """

    job = (
        db.query(PrintJob)
        .filter(
            PrintJob.id == job_id
        )
        .first()
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

    lines = (
        db.query(PrintJobLine)
        .filter(
            PrintJobLine.job_id == job.id
        )
        .all()
    )

    if not lines:

        raise HTTPException(
            status_code=400,
            detail="Le lot est vide"
        )

    assets = []

    for line in lines:

        asset = (
            db.query(Asset)
            .filter(
                Asset.id == line.asset_id
            )
            .first()
        )

        if asset:
            assets.append(asset)

    already_generated = (
        ReprintService.has_generated_before(
            db,
            job.id
        )
    )

    if already_generated:

        raise HTTPException(
            status_code=409,
            detail=(
                "Ce lot a déjà été généré. "
                "Utilisez la réimpression."
            )
        )

    generator = CommandGenerator()

    filename = generator.generate(
        job_id=job.id,
        assets=assets
    )

    job.generated_file = filename
    job.generated_at = datetime.now(UTC)
    job.status = "GENERATED"

    history = PrintHistory(
        job_id=job.id,
        username=current_user["sub"],
        action="GENERATED",
        file_name=filename,
        labels_count=job.labels_count
    )

    db.add(history)

    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "generated_file": filename,
        "status": job.status
    }


@router.get("/jobs/{job_id}/file")
def download_job_file(
    job_id: int,
    db: Session = Depends(get_db)
):

    job = (
        db.query(PrintJob)
        .filter(
            PrintJob.id == job_id
        )
        .first()
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

    if not job.generated_file:

        raise HTTPException(
            status_code=400,
            detail="Aucun fichier généré"
        )

    file_path = (
        BASE_DIR
        / "generated"
        / job.generated_file
    )

    if not file_path.exists():

        raise HTTPException(
            status_code=404,
            detail="Fichier introuvable"
        )

    return FileResponse(
        path=file_path,
        filename=job.generated_file,
        media_type="text/plain"
    )


@router.post("/jobs/{job_id}/reprint")
def reprint_job(
    job_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Réimpression d'un lot existant
    """

    job = (
        db.query(PrintJob)
        .filter(
            PrintJob.id == job_id
        )
        .first()
    )

    if not job:

        raise HTTPException(
            status_code=404,
            detail="Lot introuvable"
        )

    ReprintService.register_reprint(
        db=db,
        job=job,
        username=current_user["sub"]
    )

    return {
        "job_id": job.id,
        "status": "REPRINTED"
    }
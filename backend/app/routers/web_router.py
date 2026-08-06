from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi import Query
from fastapi import Form
from fastapi.responses import RedirectResponse
from fastapi import HTTPException

from sqlalchemy.orm import Session

from app.database import get_db

from app.models.asset_model import Asset
from app.models.import_model import Import
from app.models.print_job_model import PrintJob
from app.models.print_history_model import PrintHistory
from app.models.print_job_model import PrintJob
from app.models.print_job_line_model import PrintJobLine

from datetime import UTC
from datetime import datetime

from app.services.cmd_generator import CommandGenerator

router = APIRouter(
    tags=["Web"]
)

templates = Jinja2Templates(
    directory="app/templates"
)


@router.get("/dashboard")
def dashboard(
    request: Request,
    db: Session = Depends(get_db)
):

    imports_count = (
        db.query(Import)
        .count()
    )

    assets_count = (
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

    history_count = (
        db.query(PrintHistory)
        .count()
    )

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "imports_count": imports_count,
            "assets_count": assets_count,
            "jobs_count": jobs_count,
            "history_count": history_count
        }
    )

@router.get("/assets")
def assets(
    request: Request,
    q: str = Query(default=""),
    active_only: bool = False,
    page: int = 1,
    db: Session = Depends(get_db)
):

    query = db.query(Asset)

    if q:

        query = query.filter(
            Asset.bien_designation.ilike(
                f"%{q}%"
            )
        )

    if active_only:

        query = query.filter(
            Asset.is_active == True
        )

    page_size = 10

    total = query.count()

    assets_list = (
        query
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="assets.html",
        context={
            "assets": assets_list,
            "q": q,
            "active_only": active_only,
            "page": page,
            "total": total,
            "page_size": page_size
        }
    )

@router.post("/jobs/create")
def create_job_from_inventory(
    asset_ids: list[int] = Form(default=[]),
    db: Session = Depends(get_db)
):
    """
    Création d'un lot à partir des biens cochés.
    """

    if not asset_ids:

        # Aucun bien coché : retour à l'inventaire
        return RedirectResponse(
            url="/assets?error=no_selection",
            status_code=303
        )

    assets = (
        db.query(Asset)
        .filter(
            Asset.id.in_(asset_ids)
        )
        .all()
    )

    if not assets:

        raise HTTPException(
            status_code=400,
            detail="Aucun bien sélectionné"
        )

    job = PrintJob(
        created_by="web_user",
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

    return RedirectResponse(
        url=f"/jobs/{job.id}",
        status_code=303
    )

@router.get("/jobs/{job_id}")
def job_detail(
    request: Request,
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
            assets.append(asset)

    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={
            "job": job,
            "assets": assets
        }
    )

@router.get("/jobs")
def jobs(
    request: Request,
    db: Session = Depends(get_db)
):

    jobs = (
        db.query(PrintJob)
        .order_by(
            PrintJob.id.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "jobs": jobs
        }
    )

@router.get("/history")
def history(
    request: Request,
    db: Session = Depends(get_db)
):

    history_list = (
        db.query(PrintHistory)
        .order_by(
            PrintHistory.id.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "history": history_list
        }
    )

@router.post("/jobs/{job_id}/generate")
def generate_job(
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
            assets.append(asset)

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
        username="web_user",
        action="GENERATED",
        file_name=filename,
        labels_count=job.labels_count
    )

    db.add(history)

    db.commit()

    return RedirectResponse(
        url=f"/jobs/{job.id}",
        status_code=303
    )
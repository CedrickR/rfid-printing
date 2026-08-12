import logging
from types import SimpleNamespace

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi import Query
from fastapi import Form
from fastapi import File
from fastapi import UploadFile
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi import HTTPException

from sqlalchemy import cast
from sqlalchemy import Integer
from sqlalchemy.orm import Session

from app.database import get_db

from app.models.asset_model import Asset
from app.models.import_model import Import
from app.models.print_job_model import PrintJob
from app.models.print_history_model import PrintHistory
from app.models.print_job_line_model import PrintJobLine

from app.auth import authenticate_user
from app.auth import create_access_token
from app.auth import get_current_user_web
from app.auth import require_manager
from app.auth import set_auth_cookie
from app.auth import clear_auth_cookie

from app.services.print_job_service import (
    PrintJobService,
    EmptyPrintJobError,
    AlreadyGeneratedError,
)
from app.services.import_service import (
    ImportService,
    InvalidEncodingError,
    MissingColumnsError,
    CsvReadError,
    DuplicateBienIdError,
)
from app.services.cmd_template_service import CmdTemplateService
from app.services.cmd_generator import (
    CommandGenerator,
    ASSET_PLACEHOLDERS,
    JOB_PLACEHOLDERS,
)

logger = logging.getLogger("rfid_printing")

router = APIRouter(
    tags=["Web"]
)

templates = Jinja2Templates(
    directory="app/templates"
)


@router.get("/login")
def login_page(
    request: Request,
    next: str = "/dashboard"
):

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": None,
            "next": next
        }
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/dashboard"),
    db: Session = Depends(get_db)
):

    user = authenticate_user(db, username, password)

    if not user:

        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "error": "Identifiant ou mot de passe invalide.",
                "next": next
            },
            status_code=401
        )

    token = create_access_token(
        {
            "sub": user.username,
            "role": user.role
        }
    )

    redirect_to = next if next.startswith("/") else "/dashboard"

    response = RedirectResponse(
        url=redirect_to,
        status_code=303
    )

    set_auth_cookie(response, token)

    return response


@router.get("/logout")
def logout():

    response = RedirectResponse(
        url="/login",
        status_code=303
    )

    clear_auth_cookie(response)

    return response


@router.get("/dashboard")
def dashboard(
    request: Request,
    current_user=Depends(get_current_user_web),
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
            "history_count": history_count,
            "role": current_user["role"]
        }
    )


@router.post("/admin/reset-database")
def reset_database(
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Vide les données métier (biens, imports, lots, historique). Les
    comptes utilisateurs sont conservés pour ne pas bloquer l'accès.
    Réservé aux gestionnaires : action irréversible.
    """

    require_manager(current_user)

    db.query(PrintHistory).delete()
    db.query(PrintJobLine).delete()
    db.query(PrintJob).delete()
    db.query(Asset).delete()
    db.query(Import).delete()

    db.commit()

    logger.warning(
        "Base de données réinitialisée par %s",
        current_user["sub"]
    )

    return RedirectResponse(
        url="/dashboard?reset=1",
        status_code=303
    )


def _sample_asset_for_preview(db: Session):
    """
    Bien réel pour l'aperçu du gabarit si l'inventaire n'est pas vide,
    sinon un bien fictif pour que tous les placeholders restent
    visibles même sur une base vide.
    """

    asset = db.query(Asset).first()

    if asset:
        return asset

    return SimpleNamespace(
        bien_id="EXEMPLE001",
        bien_designation="Bien d'exemple",
        bien_amort_date_sortie=None,
        is_active=True,
        local_numero="00000001",
        immeuble_libelle="IMMEUBLE EXEMPLE",
        niveau_libelle="NIVEAU EXEMPLE",
        local_libelle="LOCAL EXEMPLE"
    )


@router.get("/settings/cmd-template")
def cmd_template_page(
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    template = CmdTemplateService.get_current(db)

    return templates.TemplateResponse(
        request=request,
        name="cmd_template.html",
        context={
            "header_template": template.header_template,
            "line_template": template.line_template,
            "asset_placeholders": sorted(ASSET_PLACEHOLDERS.keys()),
            "job_placeholders": sorted(JOB_PLACEHOLDERS.keys()),
            "error": None
        }
    )


@router.post("/settings/cmd-template")
def cmd_template_update(
    request: Request,
    header_template: str = Form(...),
    line_template: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    if not line_template.strip():

        return templates.TemplateResponse(
            request=request,
            name="cmd_template.html",
            context={
                "header_template": header_template,
                "line_template": line_template,
                "asset_placeholders": sorted(ASSET_PLACEHOLDERS.keys()),
                "job_placeholders": sorted(JOB_PLACEHOLDERS.keys()),
                "error": "Le gabarit de ligne ne peut pas être vide."
            },
            status_code=400
        )

    CmdTemplateService.update(
        db,
        header_template,
        line_template,
        current_user["sub"]
    )

    logger.warning(
        "Gabarit CMD modifié par %s",
        current_user["sub"]
    )

    return RedirectResponse(
        url="/settings/cmd-template?saved=1",
        status_code=303
    )


@router.post("/settings/cmd-template/preview")
def cmd_template_preview(
    header_template: str = Form(...),
    line_template: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    sample_asset = _sample_asset_for_preview(db)

    generator = CommandGenerator()

    return {
        "header": generator.render_template(
            header_template,
            JOB_PLACEHOLDERS,
            42
        ),
        "line": generator.render_template(
            line_template,
            ASSET_PLACEHOLDERS,
            sample_asset
        )
    }


def _import_error_message(exc: Exception) -> str:

    if isinstance(exc, InvalidEncodingError):
        return "Encodage de fichier invalide : UTF-8 attendu."

    if isinstance(exc, MissingColumnsError):
        return f"Colonnes manquantes : {', '.join(exc.missing_columns)}"

    if isinstance(exc, CsvReadError):
        return f"Erreur lecture CSV : {exc.original_error}"

    if isinstance(exc, DuplicateBienIdError):
        shown = exc.duplicated_ids[:20]
        suffix = (
            f" (et {len(exc.duplicated_ids) - 20} de plus)"
            if len(exc.duplicated_ids) > 20
            else ""
        )
        return (
            "bien_id en doublon dans le fichier : "
            f"{', '.join(shown)}{suffix}"
        )

    return "Fichier CSV invalide."


@router.get("/import")
def import_page(
    request: Request,
    current_user=Depends(get_current_user_web)
):

    return templates.TemplateResponse(
        request=request,
        name="import.html",
        context={"error": None}
    )


@router.post("/import/preview")
async def import_preview(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Aperçu du CSV (colonnes détectées, compteurs) sans écriture en base.
    Appelé en Ajax depuis la page d'import.
    """

    if not file.filename.lower().endswith(".csv"):
        return JSONResponse(
            status_code=400,
            content={"error": "Le fichier doit être un CSV"}
        )

    content = await file.read()

    try:
        _, summary = ImportService.validate(content, db)

    except (
        InvalidEncodingError,
        MissingColumnsError,
        CsvReadError,
        DuplicateBienIdError
    ) as e:
        return JSONResponse(
            status_code=400,
            content={"error": _import_error_message(e)}
        )

    return summary


@router.post("/import")
async def import_submit(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    if not file.filename.lower().endswith(".csv"):

        return templates.TemplateResponse(
            request=request,
            name="import.html",
            context={"error": "Le fichier doit être un CSV"},
            status_code=400
        )

    content = await file.read()

    try:
        df, summary = ImportService.validate(content, db)

    except (
        InvalidEncodingError,
        MissingColumnsError,
        CsvReadError,
        DuplicateBienIdError
    ) as e:

        return templates.TemplateResponse(
            request=request,
            name="import.html",
            context={"error": _import_error_message(e)},
            status_code=400
        )

    ImportService.commit(
        db,
        df,
        file.filename,
        current_user["sub"]
    )

    return RedirectResponse(
        url=(
            "/dashboard?imported=1"
            f"&total={summary['total_rows']}"
            f"&active={summary['active_assets']}"
            f"&excluded={summary['excluded_assets']}"
            f"&invalid={summary['invalid_rows']}"
            f"&existing={summary['already_existing']}"
        ),
        status_code=303
    )


def _distinct_values(db: Session, column):

    return sorted(
        value
        for (value,) in (
            db.query(column)
            .filter(column.isnot(None))
            .filter(column != "")
            .distinct()
            .all()
        )
    )


@router.get("/assets")
def assets(
    request: Request,
    q: str = Query(default=""),
    active_only: bool = False,
    bien_id_from: str = Query(default=""),
    bien_id_to: str = Query(default=""),
    immeuble: str = Query(default=""),
    niveau: str = Query(default=""),
    local: str = Query(default=""),
    page: int = 1,
    current_user=Depends(get_current_user_web),
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

    # bien_id est stocké en texte mais représente un numéro : on caste
    # en entier pour une vraie comparaison numérique (ex. 9 < 10), pas
    # une comparaison lexicographique sur la chaîne. Une valeur non
    # numérique dans le champ est simplement ignorée (filtre non
    # appliqué) plutôt que de faire planter la recherche.
    if bien_id_from:

        try:
            query = query.filter(
                cast(Asset.bien_id, Integer) >= int(bien_id_from)
            )
        except ValueError:
            pass

    if bien_id_to:

        try:
            query = query.filter(
                cast(Asset.bien_id, Integer) <= int(bien_id_to)
            )
        except ValueError:
            pass

    if immeuble:

        query = query.filter(
            Asset.immeuble_libelle == immeuble
        )

    if niveau:

        query = query.filter(
            Asset.niveau_libelle == niveau
        )

    if local:

        query = query.filter(
            Asset.local_libelle == local
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
            "bien_id_from": bien_id_from,
            "bien_id_to": bien_id_to,
            "immeuble": immeuble,
            "niveau": niveau,
            "local": local,
            "immeuble_options": _distinct_values(db, Asset.immeuble_libelle),
            "niveau_options": _distinct_values(db, Asset.niveau_libelle),
            "local_options": _distinct_values(db, Asset.local_libelle),
            "page": page,
            "total": total,
            "page_size": page_size
        }
    )

@router.post("/jobs/create")
def create_job_from_inventory(
    asset_ids: list[int] = Form(default=[]),
    current_user=Depends(get_current_user_web),
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

    return RedirectResponse(
        url=f"/jobs/{job.id}",
        status_code=303
    )

@router.get("/jobs/{job_id}")
def job_detail(
    request: Request,
    job_id: int,
    current_user=Depends(get_current_user_web),
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
    current_user=Depends(get_current_user_web),
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
    bien_id: str = Query(default=""),
    current_user=Depends(get_current_user_web),
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

    history_list = (
        query
        .order_by(
            PrintHistory.id.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "history": history_list,
            "bien_id": bien_id
        }
    )

@router.post("/jobs/{job_id}/generate")
def generate_job(
    job_id: int,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

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

    try:
        PrintJobService.generate(
            db,
            job,
            current_user["sub"]
        )

    except EmptyPrintJobError:

        return RedirectResponse(
            url=f"/jobs/{job.id}?error=empty",
            status_code=303
        )

    except AlreadyGeneratedError:

        return RedirectResponse(
            url=f"/jobs/{job.id}?error=already_generated",
            status_code=303
        )

    return RedirectResponse(
        url=f"/jobs/{job.id}",
        status_code=303
    )

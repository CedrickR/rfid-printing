import csv
import logging
from datetime import UTC, datetime
from io import StringIO
from types import SimpleNamespace
from urllib.parse import quote

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
from fastapi.responses import Response
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
from app.models.rfid_scan_model import RfidScanFile, RfidScanLine
from app.models.glpi_asset_model import GlpiImport, GlpiAsset

from app.auth import authenticate_user
from app.auth import create_access_token
from app.auth import get_current_user_web
from app.auth import require_admin
from app.auth import require_manager
from app.auth import set_auth_cookie
from app.auth import clear_auth_cookie
from app.auth import ROLE_READER
from app.auth import ROLES

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
from app.services.rfid_scan_service import (
    RfidScanService,
    InvalidEncodingError as RfidInvalidEncodingError,
    NoValidLineError,
    format_lieu_code,
    format_bien_code,
)
from app.services.user_service import (
    UserService,
    MIN_PASSWORD_LENGTH,
    DuplicateUsernameError,
    InvalidRoleError,
    WeakPasswordError,
    UserNotFoundError,
    LastAdminError,
    SelfDeleteError,
)
from app.services.glpi_service import (
    GlpiImportService,
    GLPI_TYPES,
    InvalidEncodingError as GlpiInvalidEncodingError,
    InvalidGlpiTypeError,
    MissingColumnsError as GlpiMissingColumnsError,
    DuplicateBienIdError as GlpiDuplicateBienIdError,
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

    if user.role == ROLE_READER:
        # Le profil lecteur n'a accès qu'à l'inventaire : "next" (page
        # d'origine, souvent /dashboard) ne lui est de toute façon pas
        # accessible.
        redirect_to = "/assets"
    else:
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

    require_manager(current_user)

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
    Réservé aux administrateurs : action irréversible.
    """

    require_admin(current_user)

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


def _render_users_page(
    request: Request,
    db: Session,
    error: str = None,
    status_code: int = 200
):

    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context={
            "users": UserService.list_users(db),
            "roles": ROLES,
            "error": error
        },
        status_code=status_code
    )


def _user_error_message(exc: Exception) -> str:

    if isinstance(exc, DuplicateUsernameError):
        return "Identifiant déjà utilisé ou invalide."

    if isinstance(exc, InvalidRoleError):
        return "Profil invalide."

    if isinstance(exc, WeakPasswordError):
        return (
            "Le mot de passe doit contenir au moins "
            f"{MIN_PASSWORD_LENGTH} caractères."
        )

    if isinstance(exc, LastAdminError):
        return "Impossible : il doit rester au moins un administrateur."

    if isinstance(exc, SelfDeleteError):
        return "Impossible de supprimer votre propre compte."

    return "Action impossible."


@router.get("/admin/users")
def users_page(
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_admin(current_user)

    return _render_users_page(request, db)


@router.post("/admin/users")
def users_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_admin(current_user)

    try:
        UserService.create_user(db, username, password, role)

    except (
        DuplicateUsernameError,
        InvalidRoleError,
        WeakPasswordError
    ) as e:

        return _render_users_page(
            request,
            db,
            error=_user_error_message(e),
            status_code=400
        )

    logger.warning(
        "Utilisateur '%s' créé (profil %s) par %s",
        username.strip(),
        role,
        current_user["sub"]
    )

    return RedirectResponse(
        url="/admin/users?created=1",
        status_code=303
    )


@router.post("/admin/users/{user_id}/role")
def users_update_role(
    user_id: int,
    request: Request,
    role: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_admin(current_user)

    try:
        UserService.update_role(db, user_id, role)

    except UserNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    except (InvalidRoleError, LastAdminError) as e:

        return _render_users_page(
            request,
            db,
            error=_user_error_message(e),
            status_code=400
        )

    logger.warning(
        "Profil de l'utilisateur #%s changé pour %s par %s",
        user_id,
        role,
        current_user["sub"]
    )

    return RedirectResponse(
        url="/admin/users?updated=1",
        status_code=303
    )


@router.post("/admin/users/{user_id}/password")
def users_reset_password(
    user_id: int,
    request: Request,
    password: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_admin(current_user)

    try:
        UserService.reset_password(db, user_id, password)

    except UserNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    except WeakPasswordError as e:

        return _render_users_page(
            request,
            db,
            error=_user_error_message(e),
            status_code=400
        )

    logger.warning(
        "Mot de passe de l'utilisateur #%s réinitialisé par %s",
        user_id,
        current_user["sub"]
    )

    return RedirectResponse(
        url="/admin/users?password_reset=1",
        status_code=303
    )


@router.post("/admin/users/{user_id}/delete")
def users_delete(
    user_id: int,
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_admin(current_user)

    try:
        UserService.delete_user(db, user_id, current_user["sub"])

    except UserNotFoundError:

        raise HTTPException(
            status_code=404,
            detail="Utilisateur introuvable"
        )

    except (SelfDeleteError, LastAdminError) as e:

        return _render_users_page(
            request,
            db,
            error=_user_error_message(e),
            status_code=400
        )

    logger.warning(
        "Utilisateur #%s supprimé par %s",
        user_id,
        current_user["sub"]
    )

    return RedirectResponse(
        url="/admin/users?deleted=1",
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

    require_admin(current_user)

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

    require_admin(current_user)

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

    require_admin(current_user)

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

    require_manager(current_user)

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

    require_manager(current_user)

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

    require_manager(current_user)

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


def _filtered_assets_query(
    db: Session,
    q: str,
    active_only: bool,
    bien_id_from: str,
    bien_id_to: str,
    immeuble: str,
    niveau: str,
    local: str
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

    return query


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
    page_size: int = Query(default=10),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    if page_size not in (10, 25, 50):
        page_size = 10

    query = _filtered_assets_query(
        db, q, active_only, bien_id_from, bien_id_to, immeuble, niveau, local
    )

    total = query.count()

    assets_list = (
        query
        .offset(
            (page - 1) * page_size
        )
        .limit(page_size)
        .all()
    )

    last_import = (
        db.query(Import)
        .order_by(
            Import.imported_at.desc()
        )
        .first()
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
            "page_size": page_size,
            "last_import": last_import
        }
    )


@router.get("/assets/export-csv")
def export_assets_csv(
    q: str = Query(default=""),
    active_only: bool = False,
    bien_id_from: str = Query(default=""),
    bien_id_to: str = Query(default=""),
    immeuble: str = Query(default=""),
    niveau: str = Query(default=""),
    local: str = Query(default=""),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Exporte en CSV (';', avec en-tête) l'ensemble des biens correspondant
    aux critères de recherche courants (pas seulement la page affichée).
    """

    assets_list = (
        _filtered_assets_query(
            db, q, active_only, bien_id_from, bien_id_to, immeuble, niveau, local
        )
        .all()
    )

    buffer = StringIO()

    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

    writer.writerow(
        [
            "Bien ID",
            "Désignation",
            "Numéro local",
            "Immeuble",
            "Niveau",
            "Local",
            "Actif"
        ]
    )

    for asset in assets_list:
        writer.writerow(
            [
                asset.bien_id,
                asset.bien_designation,
                asset.local_numero or "",
                asset.immeuble_libelle or "",
                asset.niveau_libelle or "",
                asset.local_libelle or "",
                "Actif" if asset.is_active else "Exclu"
            ]
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"inventaire_{timestamp}.csv"

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
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

    require_manager(current_user)

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


@router.post("/assets/export-immateriel")
def export_immateriel(
    asset_ids: list[int] = Form(default=[]),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Génère un fichier CSV "inventaire immatériel" (2 colonnes, ';', sans
    en-tête) à partir des biens cochés dans l'inventaire, au même format
    que les fichiers issus d'un lecteur RFID.
    """

    require_manager(current_user)

    if not asset_ids:

        return RedirectResponse(
            url="/assets?error=no_selection",
            status_code=303
        )

    assets_list = (
        db.query(Asset)
        .filter(
            Asset.id.in_(asset_ids)
        )
        .all()
    )

    rows = [
        (asset.local_numero, asset.bien_id)
        for asset in assets_list
        if asset.local_numero
    ]

    if not rows:

        return RedirectResponse(
            url="/assets?error=no_location",
            status_code=303
        )

    buffer = StringIO()

    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

    for local_numero, bien_id in rows:
        writer.writerow(
            [
                format_lieu_code(local_numero),
                format_bien_code(bien_id)
            ]
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"inventaire_immateriel_{timestamp}.csv"

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/assets/export-rfid-reader")
def export_rfid_reader(
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Génère le fichier CSV (';', sans en-tête) destiné à alimenter le
    lecteur RFID : tous les biens actifs, Bien ID et désignation
    uniquement.
    """

    require_manager(current_user)

    assets_list = (
        db.query(Asset)
        .filter(
            Asset.is_active == True
        )
        .order_by(
            Asset.bien_id
        )
        .all()
    )

    buffer = StringIO()

    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

    for asset in assets_list:
        writer.writerow(
            [
                asset.bien_id,
                asset.bien_designation
            ]
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"lecteur_rfid_{timestamp}.csv"

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/jobs/search")
def jobs_search_and_view(
    bien_id: str = Query(default=""),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Va directement au lot correspondant au Bien ID recherché, sans
    passer par la liste. Doit être déclarée avant /jobs/{job_id} pour
    ne pas être capturée par ce pattern.
    """

    require_manager(current_user)

    if not bien_id:
        return RedirectResponse(url="/jobs", status_code=303)

    matching_job_ids = (
        db.query(PrintJobLine.job_id)
        .join(Asset, Asset.id == PrintJobLine.asset_id)
        .filter(Asset.bien_id.contains(bien_id))
        .distinct()
        .all()
    )

    job_ids = sorted(
        {row[0] for row in matching_job_ids},
        reverse=True
    )

    if not job_ids:

        return RedirectResponse(
            url=f"/jobs?bien_id={quote(bien_id)}&error=not_found",
            status_code=303
        )

    # Plusieurs lots peuvent contenir le même bien (réimpressions,
    # imports distincts...) : on ouvre le plus récent.
    return RedirectResponse(
        url=f"/jobs/{job_ids[0]}",
        status_code=303
    )


@router.get("/jobs/{job_id}")
def job_detail(
    request: Request,
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


@router.get("/jobs/{job_id}/export-csv")
def export_job_csv(
    job_id: int,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Exporte en CSV (';', avec en-tête) la liste des biens associés au lot.
    """

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

    lines = (
        db.query(PrintJobLine)
        .filter(
            PrintJobLine.job_id == job.id
        )
        .all()
    )

    buffer = StringIO()

    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

    writer.writerow(["Bien ID", "Désignation"])

    for line in lines:

        asset = (
            db.query(Asset)
            .filter(
                Asset.id == line.asset_id
            )
            .first()
        )

        if asset:
            writer.writerow([asset.bien_id, asset.bien_designation])

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"lot_{job_id}_{timestamp}.csv"

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/jobs")
def jobs(
    request: Request,
    bien_id: str = Query(default=""),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    query = db.query(PrintJob)

    if bien_id:

        matching_job_ids = (
            db.query(PrintJobLine.job_id)
            .join(Asset, Asset.id == PrintJobLine.asset_id)
            .filter(Asset.bien_id.contains(bien_id))
            .distinct()
        )

        query = query.filter(
            PrintJob.id.in_(matching_job_ids)
        )

    jobs = (
        query
        .order_by(
            PrintJob.id.desc()
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "jobs": jobs,
            "bien_id": bien_id
        }
    )

@router.get("/history")
def history(
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

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


def _rfid_scan_error_message(exc: Exception) -> str:

    if isinstance(exc, RfidInvalidEncodingError):
        return "Encodage de fichier invalide : UTF-8 attendu."

    if isinstance(exc, NoValidLineError):
        return (
            "Aucune ligne valide dans le fichier "
            "(préfixes L261/261 attendus)."
        )

    return "Fichier CSV invalide."


def _render_rfid_scan_list(request: Request, db: Session, error: str = None):

    scan_files = (
        db.query(RfidScanFile)
        .order_by(
            RfidScanFile.id.desc()
        )
        .all()
    )

    line_counts = {
        scan_file.id: (
            db.query(RfidScanLine)
            .filter(
                RfidScanLine.scan_file_id == scan_file.id
            )
            .count()
        )
        for scan_file in scan_files
    }

    return templates.TemplateResponse(
        request=request,
        name="rfid_scans.html",
        context={
            "scan_files": scan_files,
            "line_counts": line_counts,
            "error": error
        },
        status_code=400 if error else 200
    )


@router.get("/rfid-scans")
def rfid_scans_page(
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    return _render_rfid_scan_list(request, db)


@router.post("/rfid-scans")
async def rfid_scans_upload(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    if not file.filename.lower().endswith(".csv"):

        return _render_rfid_scan_list(
            request,
            db,
            error="Le fichier doit être un CSV"
        )

    content = await file.read()

    try:
        valid_lines, invalid_rows = RfidScanService.parse(content)

    except (RfidInvalidEncodingError, NoValidLineError) as e:

        return _render_rfid_scan_list(
            request,
            db,
            error=_rfid_scan_error_message(e)
        )

    scan_file, added_count, updated_count = RfidScanService.commit(
        db,
        valid_lines,
        file.filename,
        current_user["sub"]
    )

    redirect_url = (
        f"/rfid-scans/{scan_file.id}"
        f"?added={added_count}&updated={updated_count}"
    )

    if invalid_rows:
        redirect_url += f"&invalid={invalid_rows}"

    return RedirectResponse(
        url=redirect_url,
        status_code=303
    )


@router.get("/rfid-scans/{scan_file_id}")
def rfid_scan_detail(
    request: Request,
    scan_file_id: int,
    error: str = Query(default=None),
    invalid: int = Query(default=0),
    added: int = Query(default=None),
    updated: int = Query(default=None),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    scan_file = (
        db.query(RfidScanFile)
        .filter(
            RfidScanFile.id == scan_file_id
        )
        .first()
    )

    if not scan_file:

        raise HTTPException(
            status_code=404,
            detail="Fichier introuvable"
        )

    lines = (
        db.query(RfidScanLine)
        .filter(
            RfidScanLine.scan_file_id == scan_file.id
        )
        .order_by(
            RfidScanLine.id
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="rfid_scan_detail.html",
        context={
            "scan_file": scan_file,
            "lines": lines,
            "error": error,
            "invalid": invalid,
            "added": added,
            "updated": updated
        }
    )


@router.post("/rfid-scans/{scan_file_id}/lines")
def rfid_scan_line_add(
    scan_file_id: int,
    lieu_numero: str = Form(...),
    bien_id: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    scan_file = (
        db.query(RfidScanFile)
        .filter(
            RfidScanFile.id == scan_file_id
        )
        .first()
    )

    if not scan_file:

        raise HTTPException(
            status_code=404,
            detail="Fichier introuvable"
        )

    lieu_numero = lieu_numero.strip()
    bien_id = bien_id.strip()

    if not lieu_numero or not bien_id:

        return RedirectResponse(
            url=f"/rfid-scans/{scan_file_id}?error=missing_fields",
            status_code=303
        )

    duplicate = (
        db.query(RfidScanLine)
        .filter(
            RfidScanLine.bien_id == bien_id
        )
        .first()
    )

    if duplicate:

        return RedirectResponse(
            url=f"/rfid-scans/{scan_file_id}?error=duplicate_bien_id",
            status_code=303
        )

    db.add(
        RfidScanLine(
            scan_file_id=scan_file.id,
            lieu_numero=lieu_numero,
            bien_id=bien_id
        )
    )

    db.commit()

    return RedirectResponse(
        url=f"/rfid-scans/{scan_file_id}",
        status_code=303
    )


@router.post("/rfid-scans/{scan_file_id}/lines/{line_id}")
def rfid_scan_line_update(
    scan_file_id: int,
    line_id: int,
    lieu_numero: str = Form(...),
    bien_id: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    line = (
        db.query(RfidScanLine)
        .filter(
            RfidScanLine.id == line_id,
            RfidScanLine.scan_file_id == scan_file_id
        )
        .first()
    )

    if not line:

        raise HTTPException(
            status_code=404,
            detail="Ligne introuvable"
        )

    lieu_numero = lieu_numero.strip()
    bien_id = bien_id.strip()

    if not lieu_numero or not bien_id:

        return RedirectResponse(
            url=f"/rfid-scans/{scan_file_id}?error=missing_fields",
            status_code=303
        )

    duplicate = (
        db.query(RfidScanLine)
        .filter(
            RfidScanLine.bien_id == bien_id,
            RfidScanLine.id != line.id
        )
        .first()
    )

    if duplicate:

        return RedirectResponse(
            url=f"/rfid-scans/{scan_file_id}?error=duplicate_bien_id",
            status_code=303
        )

    line.lieu_numero = lieu_numero
    line.bien_id = bien_id

    db.commit()

    return RedirectResponse(
        url=f"/rfid-scans/{scan_file_id}",
        status_code=303
    )


@router.post("/rfid-scans/{scan_file_id}/lines/{line_id}/delete")
def rfid_scan_line_delete(
    scan_file_id: int,
    line_id: int,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    (
        db.query(RfidScanLine)
        .filter(
            RfidScanLine.id == line_id,
            RfidScanLine.scan_file_id == scan_file_id
        )
        .delete()
    )

    db.commit()

    return RedirectResponse(
        url=f"/rfid-scans/{scan_file_id}",
        status_code=303
    )


@router.get("/rfid-scans/{scan_file_id}/export")
def rfid_scan_export(
    scan_file_id: int,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    scan_file = (
        db.query(RfidScanFile)
        .filter(
            RfidScanFile.id == scan_file_id
        )
        .first()
    )

    if not scan_file:

        raise HTTPException(
            status_code=404,
            detail="Fichier introuvable"
        )

    lines = (
        db.query(RfidScanLine)
        .filter(
            RfidScanLine.scan_file_id == scan_file.id
        )
        .order_by(
            RfidScanLine.id
        )
        .all()
    )

    content = RfidScanService.export_csv(lines)
    filename = RfidScanService.export_filename()

    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def _glpi_error_message(exc: Exception) -> str:

    if isinstance(exc, GlpiInvalidEncodingError):
        return "Encodage de fichier invalide : UTF-8 attendu."

    if isinstance(exc, GlpiMissingColumnsError):
        return f"Colonnes manquantes : {', '.join(exc.missing_columns)}"

    if isinstance(exc, GlpiDuplicateBienIdError):
        shown = exc.duplicated_ids[:20]
        suffix = (
            f" (et {len(exc.duplicated_ids) - 20} de plus)"
            if len(exc.duplicated_ids) > 20
            else ""
        )
        return (
            "Numéro d'inventaire en doublon dans le fichier : "
            f"{', '.join(shown)}{suffix}"
        )

    return "Fichier GLPI invalide."


def _local_options(db: Session):
    """
    Paires (numéro local, désignation) distinctes connues dans
    l'inventaire, pour la liste déroulante de correction.
    """

    return (
        db.query(Asset.local_numero, Asset.local_libelle)
        .filter(Asset.local_numero.isnot(None))
        .filter(Asset.local_numero != "")
        .filter(Asset.local_libelle.isnot(None))
        .filter(Asset.local_libelle != "")
        .distinct()
        .order_by(Asset.local_libelle)
        .all()
    )


def _location_details_by_numero(db: Session):
    """
    Pour chaque numéro local distinct connu dans l'inventaire, ses
    autres colonnes de lieu (désignation, immeuble, niveau) — pour
    reconstituer les colonnes de lieu complètes du numéro local choisi
    lors de la correction, plutôt que celles (potentiellement obsolètes)
    du bien lui-même.
    """

    rows = (
        db.query(
            Asset.local_numero,
            Asset.local_libelle,
            Asset.immeuble_libelle,
            Asset.niveau_libelle
        )
        .filter(Asset.local_numero.isnot(None))
        .filter(Asset.local_numero != "")
        .all()
    )

    details = {}

    for numero, libelle, immeuble, niveau in rows:
        if numero not in details:
            details[numero] = {
                "local_libelle": libelle,
                "immeuble_libelle": immeuble,
                "niveau_libelle": niveau
            }

    return details


def _glpi_discrepancies(db: Session):
    """
    Biens connus à la fois dans l'inventaire et dans un import GLPI,
    dont le numéro local (inventaire) diffère du numéro de la pièce
    (GLPI).
    """

    rows = (
        db.query(Asset, GlpiAsset)
        .join(
            GlpiAsset,
            GlpiAsset.bien_id == Asset.bien_id
        )
        .order_by(
            Asset.bien_id
        )
        .all()
    )

    return [
        (asset, glpi_asset)
        for asset, glpi_asset in rows
        if (asset.local_numero or "").strip()
        != (glpi_asset.numero_piece or "").strip()
    ]


def _render_glpi_locations(
    request: Request,
    db: Session,
    error: str = None,
    status_code: int = 200
):

    imports_by_type = {
        glpi_type: (
            db.query(GlpiImport)
            .filter(GlpiImport.glpi_type == glpi_type)
            .order_by(GlpiImport.imported_at.desc())
            .first()
        )
        for glpi_type in GLPI_TYPES
    }

    return templates.TemplateResponse(
        request=request,
        name="glpi_locations.html",
        context={
            "glpi_types": GLPI_TYPES,
            "imports_by_type": imports_by_type,
            "discrepancies": _glpi_discrepancies(db),
            "local_options": _local_options(db),
            "error": error
        },
        status_code=status_code
    )


@router.get("/glpi-locations")
def glpi_locations_page(
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    return _render_glpi_locations(request, db)


@router.post("/glpi-locations")
async def glpi_locations_upload(
    request: Request,
    file: UploadFile = File(...),
    glpi_type: str = Form(...),
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):

    require_manager(current_user)

    if glpi_type not in GLPI_TYPES:

        return _render_glpi_locations(
            request,
            db,
            error="Type GLPI invalide.",
            status_code=400
        )

    if not file.filename.lower().endswith(".csv"):

        return _render_glpi_locations(
            request,
            db,
            error="Le fichier doit être un CSV",
            status_code=400
        )

    content = await file.read()

    try:
        rows = GlpiImportService.parse(content)

    except (
        GlpiInvalidEncodingError,
        GlpiMissingColumnsError,
        GlpiDuplicateBienIdError
    ) as e:

        return _render_glpi_locations(
            request,
            db,
            error=_glpi_error_message(e),
            status_code=400
        )

    glpi_import = GlpiImportService.commit(
        db,
        rows,
        glpi_type,
        file.filename,
        current_user["sub"]
    )

    return RedirectResponse(
        url=(
            "/glpi-locations?imported=1"
            f"&added={glpi_import.added_count}"
            f"&updated={glpi_import.updated_count}"
        ),
        status_code=303
    )


@router.post("/glpi-locations/export-csv")
async def glpi_locations_export_csv(
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Génère un fichier CSV (';', avec en-tête) Bien ID / numéro local
    corrigé, à partir des lignes cochées et de la correction choisie
    dans la liste déroulante de chaque ligne.
    """

    require_manager(current_user)

    form = await request.form()

    asset_ids = form.getlist("asset_ids")

    if not asset_ids:

        return RedirectResponse(
            url="/glpi-locations?error=no_selection",
            status_code=303
        )

    buffer = StringIO()

    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

    writer.writerow(["Bien ID", "Numéro local"])

    for asset_id in asset_ids:

        asset = (
            db.query(Asset)
            .filter(
                Asset.id == int(asset_id)
            )
            .first()
        )

        if not asset:
            continue

        corrected = form.get(f"local_choice_{asset_id}")

        writer.writerow(
            [
                asset.bien_id,
                corrected or asset.local_numero or ""
            ]
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"codes_lieux_{timestamp}.csv"

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/glpi-locations/export-csv-complet")
async def glpi_locations_export_csv_complet(
    request: Request,
    current_user=Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Comme /glpi-locations/export-csv, mais avec en plus les colonnes de
    lieu (immeuble, niveau, local) correspondant au numéro local
    corrigé, plutôt que le seul numéro.
    """

    require_manager(current_user)

    form = await request.form()

    asset_ids = form.getlist("asset_ids")

    if not asset_ids:

        return RedirectResponse(
            url="/glpi-locations?error=no_selection",
            status_code=303
        )

    location_details = _location_details_by_numero(db)

    buffer = StringIO()

    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

    writer.writerow(["Bien ID", "Numéro local", "Immeuble", "Niveau", "Local"])

    for asset_id in asset_ids:

        asset = (
            db.query(Asset)
            .filter(
                Asset.id == int(asset_id)
            )
            .first()
        )

        if not asset:
            continue

        corrected = form.get(f"local_choice_{asset_id}") or asset.local_numero or ""

        details = location_details.get(
            corrected,
            {
                "local_libelle": asset.local_libelle,
                "immeuble_libelle": asset.immeuble_libelle,
                "niveau_libelle": asset.niveau_libelle
            }
        )

        writer.writerow(
            [
                asset.bien_id,
                corrected,
                details["immeuble_libelle"] or "",
                details["niveau_libelle"] or "",
                details["local_libelle"] or ""
            ]
        )

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"codes_lieux_complet_{timestamp}.csv"

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )

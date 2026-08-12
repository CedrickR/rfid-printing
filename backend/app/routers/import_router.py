import functools

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile

from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user

from app.models.asset_model import Asset

from app.services.import_service import (
    ImportService,
    InvalidEncodingError,
    MissingColumnsError,
    CsvReadError,
    DuplicateBienIdError,
)

router = APIRouter(
    prefix="/api/import",
    tags=["Imports"]
)


def handle_import_errors(func):
    """
    Traduit les exceptions d'ImportService en réponses HTTP explicites,
    partagées par les endpoints qui valident/importent un CSV.
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):

        try:
            return await func(*args, **kwargs)

        except InvalidEncodingError:
            raise HTTPException(
                status_code=400,
                detail="Encodage de fichier invalide : UTF-8 attendu"
            )

        except MissingColumnsError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Colonnes manquantes : {', '.join(e.missing_columns)}"
            )

        except CsvReadError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Erreur lecture CSV : {str(e.original_error)}"
            )

        except DuplicateBienIdError as e:
            shown = e.duplicated_ids[:20]
            suffix = (
                f" (et {len(e.duplicated_ids) - 20} de plus)"
                if len(e.duplicated_ids) > 20
                else ""
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "bien_id en doublon dans le fichier : "
                    f"{', '.join(shown)}{suffix}"
                )
            )

    return wrapper


@router.post("/")
@handle_import_errors
async def import_csv(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Le fichier doit être un CSV"
        )

    content = await file.read()

    df, summary = ImportService.validate(content)

    new_import = ImportService.commit(
        db,
        df,
        file.filename,
        current_user["sub"]
    )

    return {
        "import_id": new_import.id,
        "filename": file.filename,
        "total_rows": summary["total_rows"],
        "active_assets": summary["active_assets"],
        "excluded_assets": summary["excluded_assets"],
        "invalid_rows": summary["invalid_rows"]
    }

@router.get("/assets-count")
def assets_count(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return {
        "assets": db.query(Asset).count()
    }

@router.get("/assets")
def get_assets(
    page: int = 1,
    size: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    offset = (page - 1) * size

    assets = (
        db.query(Asset)
        .offset(offset)
        .limit(size)
        .all()
    )

    return assets


@router.get("/assets/active")
def active_assets(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    count = (
        db.query(Asset)
        .filter(
            Asset.is_active == True
        )
        .count()
    )

    return {
        "active_assets": count
    }

@router.get("/assets/search")
def search_assets(
    q: str,
    page: int = 1,
    size: int = 100,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):

    offset = (page - 1) * size

    results = (
        db.query(Asset)
        .filter(
            Asset.bien_designation.contains(q)
        )
        .offset(offset)
        .limit(size)
        .all()
    )

    return results

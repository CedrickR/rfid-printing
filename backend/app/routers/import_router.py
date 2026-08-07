from datetime import datetime
from io import StringIO

import pandas as pd

from fastapi import APIRouter
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import UploadFile

from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user

from app.models.import_model import Import
from app.models.asset_model import Asset

from datetime import datetime, UTC

router = APIRouter(
    prefix="/api/import",
    tags=["Imports"]
)


@router.post("/")
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

    try:
        df = pd.read_csv(
            StringIO(content.decode("utf-8")),
            sep=";"
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Erreur lecture CSV : {str(e)}"
        )

    required_columns = [
        "bien_id",
        "bien_designation",
        "bien_amort_date_sortie"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Colonnes manquantes : {', '.join(missing_columns)}"
        )

    total_rows = len(df)

    active_assets = len(
        df[
            df["bien_amort_date_sortie"].isna()
        ]
    )

    excluded_assets = total_rows - active_assets

    # Création de l'import
    new_import = Import(
        filename=file.filename,
        imported_by=current_user["sub"],
        imported_at=datetime.now(UTC),
        total_rows=total_rows,
        active_assets=active_assets,
        excluded_assets=excluded_assets
    )

    db.add(new_import)
    db.commit()
    db.refresh(new_import)

    # Enregistrement des biens
    for _, row in df.iterrows():

        is_active = pd.isna(
            row["bien_amort_date_sortie"]
        )

        asset = Asset(
            bien_id=str(row["bien_id"]),
            bien_designation=str(
                row["bien_designation"]
            ),
            bien_amort_date_sortie=(
                None
                if pd.isna(
                    row["bien_amort_date_sortie"]
                )
                else str(
                    row["bien_amort_date_sortie"]
                )
            ),
            is_active=is_active,
            import_id=new_import.id
        )

        db.add(asset)

    db.commit()

    return {
        "import_id": new_import.id,
        "filename": file.filename,
        "total_rows": total_rows,
        "active_assets": active_assets,
        "excluded_assets": excluded_assets
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
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    results = (
        db.query(Asset)
        .filter(
            Asset.bien_designation.contains(q)
        )
        .all()
    )

    return results
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

REQUIRED_COLUMNS = [
    "bien_id",
    "bien_designation",
    "bien_amort_date_sortie"
]

# Le point-virgule est le séparateur le plus courant sur les exports
# Excel FR ; la virgule reste tentée en repli pour les exports "CSV" au
# sens strict (RFC 4180).
CANDIDATE_DELIMITERS = [";", ","]


def parse_inventory_csv(raw_text: str) -> pd.DataFrame:
    """
    Lit un CSV en détectant automatiquement le séparateur (';' ou ',')
    utilisé : on retient le premier qui fait apparaître toutes les
    colonnes attendues.
    """

    last_error = None
    best_attempt = None

    for delimiter in CANDIDATE_DELIMITERS:

        try:
            df = pd.read_csv(
                StringIO(raw_text),
                sep=delimiter,
                # bien_id/bien_designation en texte : évite qu'une valeur
                # manquante ailleurs dans la colonne ne fasse basculer des
                # identifiants numériques en flottant (ex. "1001.0").
                dtype={
                    "bien_id": str,
                    "bien_designation": str
                }
            )

        except Exception as e:
            last_error = e
            continue

        missing_columns = [
            col
            for col in REQUIRED_COLUMNS
            if col not in df.columns
        ]

        if not missing_columns:
            return df

        if best_attempt is None:
            best_attempt = (df, missing_columns)

    if best_attempt is not None:
        df, missing_columns = best_attempt

        raise HTTPException(
            status_code=400,
            detail=f"Colonnes manquantes : {', '.join(missing_columns)}"
        )

    raise HTTPException(
        status_code=400,
        detail=f"Erreur lecture CSV : {str(last_error)}"
    )


def clean_inventory_rows(df: pd.DataFrame):
    """
    Normalise bien_id/bien_designation (espaces superflus) puis sépare les
    lignes exploitables des lignes invalides (bien_id ou désignation
    manquants). Retourne (df_valides, nombre_de_lignes_invalides).
    """

    df = df.copy()

    df["bien_id"] = (
        df["bien_id"]
        .astype(str)
        .str.strip()
        .replace({"nan": None, "": None})
    )

    df["bien_designation"] = (
        df["bien_designation"]
        .astype(str)
        .str.strip()
        .replace({"nan": None, "": None})
    )

    valid_mask = (
        df["bien_id"].notna()
        & df["bien_designation"].notna()
    )

    invalid_rows = int((~valid_mask).sum())

    return df[valid_mask], invalid_rows


def check_no_duplicate_bien_id(df: pd.DataFrame):

    duplicated_ids = (
        df["bien_id"][df["bien_id"].duplicated()]
        .unique()
        .tolist()
    )

    if duplicated_ids:

        shown = duplicated_ids[:20]
        suffix = (
            f" (et {len(duplicated_ids) - 20} de plus)"
            if len(duplicated_ids) > 20
            else ""
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "bien_id en doublon dans le fichier : "
                f"{', '.join(shown)}{suffix}"
            )
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
        raw_text = content.decode("utf-8")

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Encodage de fichier invalide : UTF-8 attendu"
        )

    df = parse_inventory_csv(raw_text)

    df, invalid_rows = clean_inventory_rows(df)

    check_no_duplicate_bien_id(df)

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
            bien_id=row["bien_id"],
            bien_designation=row["bien_designation"],
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
        "excluded_assets": excluded_assets,
        "invalid_rows": invalid_rows
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
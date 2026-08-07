from datetime import UTC, datetime
from io import StringIO

import pandas as pd

from app.models.asset_model import Asset
from app.models.import_model import Import

REQUIRED_COLUMNS = [
    "bien_id",
    "bien_designation",
    "bien_amort_date_sortie"
]

# Le point-virgule est le séparateur le plus courant sur les exports
# Excel FR ; la virgule reste tentée en repli pour les exports "CSV" au
# sens strict (RFC 4180).
CANDIDATE_DELIMITERS = [";", ","]


class InvalidEncodingError(Exception):
    pass


class MissingColumnsError(Exception):
    def __init__(self, missing_columns):
        self.missing_columns = missing_columns


class CsvReadError(Exception):
    def __init__(self, original_error):
        self.original_error = original_error


class DuplicateBienIdError(Exception):
    def __init__(self, duplicated_ids):
        self.duplicated_ids = duplicated_ids


class ImportService:
    """
    Lecture, validation et import du CSV d'inventaire, partagées entre
    l'API (import_router) et l'UI Jinja2 (web_router : aperçu + import).
    """

    @staticmethod
    def decode(content: bytes) -> str:

        try:
            return content.decode("utf-8")

        except UnicodeDecodeError:
            raise InvalidEncodingError()

    @staticmethod
    def parse(raw_text: str) -> pd.DataFrame:
        """
        Détecte automatiquement le séparateur (';' ou ',') : on retient
        le premier qui fait apparaître toutes les colonnes attendues.
        """

        last_error = None
        best_attempt = None

        for delimiter in CANDIDATE_DELIMITERS:

            try:
                df = pd.read_csv(
                    StringIO(raw_text),
                    sep=delimiter,
                    # bien_id/bien_designation en texte : évite qu'une
                    # valeur manquante ailleurs dans la colonne ne fasse
                    # basculer des identifiants numériques en flottant
                    # (ex. "1001.0").
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
                best_attempt = missing_columns

        if best_attempt is not None:
            raise MissingColumnsError(best_attempt)

        raise CsvReadError(last_error)

    @staticmethod
    def clean(df: pd.DataFrame):
        """
        Normalise bien_id/bien_designation (espaces superflus) puis
        sépare les lignes exploitables des lignes invalides (bien_id ou
        désignation manquants). Retourne (df_valides, nb_lignes_invalides).
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

    @staticmethod
    def check_no_duplicate_bien_id(df: pd.DataFrame):

        duplicated_ids = (
            df["bien_id"][df["bien_id"].duplicated()]
            .unique()
            .tolist()
        )

        if duplicated_ids:
            raise DuplicateBienIdError(duplicated_ids)

    @staticmethod
    def validate(content: bytes):
        """
        Décode, parse et valide le CSV sans toucher la base. Retourne
        (df_valide, résumé) où résumé contient les colonnes détectées et
        les compteurs de lignes.
        """

        raw_text = ImportService.decode(content)

        df = ImportService.parse(raw_text)

        columns = df.columns.tolist()

        df, invalid_rows = ImportService.clean(df)

        ImportService.check_no_duplicate_bien_id(df)

        total_rows = len(df)

        active_assets = int(
            df["bien_amort_date_sortie"].isna().sum()
        )

        excluded_assets = total_rows - active_assets

        summary = {
            "columns": columns,
            "total_rows": total_rows,
            "active_assets": active_assets,
            "excluded_assets": excluded_assets,
            "invalid_rows": invalid_rows
        }

        return df, summary

    @staticmethod
    def commit(db, df: pd.DataFrame, filename: str, username: str) -> Import:
        """
        Enregistre l'import et les biens en base à partir d'un DataFrame
        déjà validé par validate().
        """

        total_rows = len(df)

        active_assets = int(
            df["bien_amort_date_sortie"].isna().sum()
        )

        excluded_assets = total_rows - active_assets

        new_import = Import(
            filename=filename,
            imported_by=username,
            imported_at=datetime.now(UTC),
            total_rows=total_rows,
            active_assets=active_assets,
            excluded_assets=excluded_assets
        )

        db.add(new_import)
        db.commit()
        db.refresh(new_import)

        for _, row in df.iterrows():

            is_active = pd.isna(
                row["bien_amort_date_sortie"]
            )

            asset = Asset(
                bien_id=row["bien_id"],
                bien_designation=row["bien_designation"],
                bien_amort_date_sortie=(
                    None
                    if pd.isna(row["bien_amort_date_sortie"])
                    else str(row["bien_amort_date_sortie"])
                ),
                is_active=is_active,
                import_id=new_import.id
            )

            db.add(asset)

        db.commit()

        return new_import

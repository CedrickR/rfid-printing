from datetime import UTC, datetime
from io import StringIO

import pandas as pd

from app.models.asset_model import Asset
from app.models.import_model import Import

# Le fichier vient tel quel du logiciel de gestion d'inventaire. Ces 3
# colonnes sont indispensables (l'import échoue si l'une manque) et sont
# ramenées à nos champs internes (bien_id, bien_designation,
# bien_amort_date_sortie), inchangés par ailleurs (déjà utilisés partout
# dans le modèle, les routes et les templates).
REQUIRED_COLUMN_MAP = {
    "numero": "bien_id",
    "libelle": "bien_designation",
    "sortie": "bien_amort_date_sortie"
}

# Colonnes de localisation : exploitées si présentes dans le fichier,
# mais ne font pas échouer l'import si elles sont absentes (variantes
# d'export possibles). Les lignes qui n'ont pas de valeur (ex. biens
# déjà sortis) restent importées, juste sans localisation.
OPTIONAL_COLUMN_MAP = {
    "local_numero": "local_numero",
    "immeuble_libelle": "immeuble_libelle",
    "niveau_libelle": "niveau_libelle",
    "local_libelle": "local_libelle"
}

REQUIRED_COLUMNS = list(REQUIRED_COLUMN_MAP.keys())

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
    def parse(raw_text: str):
        """
        Détecte automatiquement le séparateur (';' ou ',') : on retient
        le premier qui fait apparaître les 3 colonnes obligatoires
        (numero/libelle/sortie). Retourne (df, colonnes_détectées) où le
        df est ramené à nos noms de champs internes (bien_id,
        bien_designation, bien_amort_date_sortie, + les colonnes de
        localisation présentes) et purgé des colonnes non utilisées. Les
        colonnes de localisation absentes du fichier sont ajoutées à
        None pour que la suite du traitement les trouve toujours.
        """

        last_error = None
        best_attempt = None

        dtype_hints = {
            col: str
            for col in list(REQUIRED_COLUMN_MAP) + list(OPTIONAL_COLUMN_MAP)
            # numero/libelle en texte : évite qu'une valeur manquante
            # ailleurs dans la colonne ne fasse basculer des identifiants
            # numériques en flottant (ex. "1001.0", ou une perte de zéro
            # non significatif sur local_numero, ex. "01100021").
        }

        for delimiter in CANDIDATE_DELIMITERS:

            try:
                df = pd.read_csv(
                    StringIO(raw_text),
                    sep=delimiter,
                    dtype=dtype_hints
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

                detected_columns = df.columns.tolist()

                rename_map = dict(REQUIRED_COLUMN_MAP)

                for source_col, target_col in OPTIONAL_COLUMN_MAP.items():
                    if source_col in df.columns:
                        rename_map[source_col] = target_col

                df = df.rename(columns=rename_map)

                for target_col in OPTIONAL_COLUMN_MAP.values():
                    if target_col not in df.columns:
                        df[target_col] = None

                selected_columns = (
                    list(REQUIRED_COLUMN_MAP.values())
                    + list(OPTIONAL_COLUMN_MAP.values())
                )

                df = df[selected_columns]

                return df, detected_columns

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
    def validate(content: bytes, db):
        """
        Décode, parse et valide le CSV. Retourne (df_à_traiter, résumé)
        où résumé contient les colonnes détectées et les compteurs de
        lignes. df_à_traiter contient toutes les lignes valides
        (nouvelles ou déjà connues) : import incrémental, un bien_id
        déjà en base est mis à jour plutôt que réinséré en double.
        """

        raw_text = ImportService.decode(content)

        df, columns = ImportService.parse(raw_text)

        df, invalid_rows = ImportService.clean(df)

        ImportService.check_no_duplicate_bien_id(df)

        existing_bien_ids = {
            bien_id
            for (bien_id,) in db.query(Asset.bien_id).all()
        }

        is_new_mask = ~df["bien_id"].isin(existing_bien_ids)

        added_count = int(is_new_mask.sum())
        updated_count = len(df) - added_count

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
            "invalid_rows": invalid_rows,
            "added_count": added_count,
            "updated_count": updated_count
        }

        return df, summary

    @staticmethod
    def commit(db, df: pd.DataFrame, filename: str, username: str):
        """
        Enregistre l'import et les biens en base à partir d'un DataFrame
        déjà validé par validate() : ajoute les bien_id inconnus, met à
        jour ceux déjà présents (jamais de doublon). Retourne
        (import, added_count, updated_count).
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

        added_count = 0
        updated_count = 0

        for _, row in df.iterrows():

            is_active = pd.isna(
                row["bien_amort_date_sortie"]
            )

            bien_amort_date_sortie = (
                None
                if pd.isna(row["bien_amort_date_sortie"])
                else str(row["bien_amort_date_sortie"])
            )
            local_numero = (
                None
                if pd.isna(row["local_numero"])
                else str(row["local_numero"])
            )
            immeuble_libelle = (
                None
                if pd.isna(row["immeuble_libelle"])
                else str(row["immeuble_libelle"])
            )
            niveau_libelle = (
                None
                if pd.isna(row["niveau_libelle"])
                else str(row["niveau_libelle"])
            )
            local_libelle = (
                None
                if pd.isna(row["local_libelle"])
                else str(row["local_libelle"])
            )

            existing = (
                db.query(Asset)
                .filter(Asset.bien_id == row["bien_id"])
                .first()
            )

            if existing:

                existing.bien_designation = row["bien_designation"]
                existing.bien_amort_date_sortie = bien_amort_date_sortie
                existing.local_numero = local_numero
                existing.immeuble_libelle = immeuble_libelle
                existing.niveau_libelle = niveau_libelle
                existing.local_libelle = local_libelle
                existing.is_active = is_active
                existing.import_id = new_import.id

                updated_count += 1

            else:

                db.add(
                    Asset(
                        bien_id=row["bien_id"],
                        bien_designation=row["bien_designation"],
                        bien_amort_date_sortie=bien_amort_date_sortie,
                        local_numero=local_numero,
                        immeuble_libelle=immeuble_libelle,
                        niveau_libelle=niveau_libelle,
                        local_libelle=local_libelle,
                        is_active=is_active,
                        import_id=new_import.id
                    )
                )

                added_count += 1

        db.commit()

        return new_import, added_count, updated_count

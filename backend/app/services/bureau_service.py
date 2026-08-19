import csv
from datetime import UTC, datetime
from io import StringIO

from app.models.bureau_model import BureauImport, BureauMapping

CODELIEU_COLUMN = "codelieu"
BATIMENT_COLUMN = "batiment"
ETAGE_COLUMN = "etage"
BUREAU_COLUMN = "bureau"
REQUIRED_COLUMNS = [
    CODELIEU_COLUMN, BATIMENT_COLUMN, ETAGE_COLUMN, BUREAU_COLUMN
]


class InvalidEncodingError(Exception):
    pass


class MissingColumnsError(Exception):
    def __init__(self, missing_columns):
        self.missing_columns = missing_columns


class DuplicateCodelieuError(Exception):
    def __init__(self, duplicated_codes):
        self.duplicated_codes = duplicated_codes


class BureauImportService:
    """
    Import du fichier CSV de correspondance bureaux (';', avec
    en-tête, colonnes codelieu/batiment/etage/bureau), pour la colonne
    "Bureau" de l'inventaire (jointure sur `Asset.local_numero`).
    """

    @staticmethod
    def parse(content: bytes):
        """
        Décode et parse le CSV. Retourne une liste de (codelieu,
        batiment, etage, bureau).
        """

        try:
            raw_text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise InvalidEncodingError()

        reader = csv.DictReader(StringIO(raw_text), delimiter=";")

        fieldnames = reader.fieldnames or []

        missing_columns = [
            col
            for col in REQUIRED_COLUMNS
            if col not in fieldnames
        ]

        if missing_columns:
            raise MissingColumnsError(missing_columns)

        rows = []
        seen_codes = set()
        duplicated_codes = []

        for row in reader:

            codelieu = (row.get(CODELIEU_COLUMN) or "").strip()
            batiment = (row.get(BATIMENT_COLUMN) or "").strip()
            etage = (row.get(ETAGE_COLUMN) or "").strip()
            bureau = (row.get(BUREAU_COLUMN) or "").strip()

            if not codelieu:
                continue

            if codelieu in seen_codes:
                duplicated_codes.append(codelieu)
                continue

            seen_codes.add(codelieu)

            rows.append((codelieu, batiment, etage, bureau))

        if duplicated_codes:
            raise DuplicateCodelieuError(duplicated_codes)

        return rows

    @staticmethod
    def commit(db, rows, filename: str, username: str) -> BureauImport:
        """
        Ajoute les nouveaux codes lieu et met à jour ceux déjà connus
        (jamais de doublon en base).
        """

        bureau_import = BureauImport(
            filename=filename,
            imported_by=username,
            imported_at=datetime.now(UTC),
            total_rows=len(rows)
        )

        db.add(bureau_import)
        db.commit()
        db.refresh(bureau_import)

        added_count = 0
        updated_count = 0

        for codelieu, batiment, etage, bureau in rows:

            existing = (
                db.query(BureauMapping)
                .filter(BureauMapping.codelieu == codelieu)
                .first()
            )

            if existing:

                existing.batiment = batiment
                existing.etage = etage
                existing.bureau = bureau
                existing.import_id = bureau_import.id
                existing.updated_at = datetime.now(UTC)

                updated_count += 1

            else:

                db.add(
                    BureauMapping(
                        codelieu=codelieu,
                        batiment=batiment,
                        etage=etage,
                        bureau=bureau,
                        import_id=bureau_import.id,
                        updated_at=datetime.now(UTC)
                    )
                )

                added_count += 1

        bureau_import.added_count = added_count
        bureau_import.updated_count = updated_count

        db.commit()

        return bureau_import

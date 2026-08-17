import csv
from datetime import UTC, datetime
from io import StringIO

from app.models.glpi_asset_model import GlpiImport, GlpiAsset

# 5 exports GLPI possibles, un fichier par type. Clé = valeur stockée en
# base (glpi_type), valeur = libellé affiché dans l'UI.
GLPI_TYPES = {
    "ordinateur": "Ordinateurs",
    "moniteur": "Moniteurs",
    "peripherique": "Périphériques",
    "logiciel": "Logiciels",
    "imprimante": "Imprimantes",
}

BIEN_ID_COLUMN = "Numéro d'inventaire"
NUMERO_PIECE_COLUMN = "Numéro de la pièce"
REQUIRED_COLUMNS = [BIEN_ID_COLUMN, NUMERO_PIECE_COLUMN]


class InvalidEncodingError(Exception):
    pass


class InvalidGlpiTypeError(Exception):
    pass


class MissingColumnsError(Exception):
    def __init__(self, missing_columns):
        self.missing_columns = missing_columns


class DuplicateBienIdError(Exception):
    def __init__(self, duplicated_ids):
        self.duplicated_ids = duplicated_ids


class GlpiImportService:
    """
    Import des exports GLPI (';', avec en-tête). Seules les colonnes
    "Numéro d'inventaire" (Bien ID) et "Numéro de la pièce" sont
    conservées, pour comparaison avec le numéro local déjà connu dans
    l'inventaire.
    """

    @staticmethod
    def parse(content: bytes):
        """
        Décode et parse le CSV. Retourne une liste de (bien_id,
        numero_piece). Lève DuplicateBienIdError si le fichier contient
        plusieurs fois le même Bien ID (cohérent avec l'import
        inventaire : on force un fichier propre plutôt que de choisir
        silencieusement une occurrence).
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
        seen_ids = set()
        duplicated_ids = []

        for row in reader:

            bien_id = (row.get(BIEN_ID_COLUMN) or "").strip()
            numero_piece = (row.get(NUMERO_PIECE_COLUMN) or "").strip()

            if not bien_id:
                continue

            if bien_id in seen_ids:
                duplicated_ids.append(bien_id)
                continue

            seen_ids.add(bien_id)

            rows.append((bien_id, numero_piece))

        if duplicated_ids:
            raise DuplicateBienIdError(duplicated_ids)

        return rows

    @staticmethod
    def commit(db, rows, glpi_type: str, filename: str, username: str) -> GlpiImport:
        """
        Ajoute les nouveaux Bien ID et met à jour le numéro de la pièce
        des Bien ID déjà connus (jamais de doublon en base).
        """

        if glpi_type not in GLPI_TYPES:
            raise InvalidGlpiTypeError()

        glpi_import = GlpiImport(
            glpi_type=glpi_type,
            filename=filename,
            imported_by=username,
            imported_at=datetime.now(UTC),
            total_rows=len(rows)
        )

        db.add(glpi_import)
        db.commit()
        db.refresh(glpi_import)

        added_count = 0
        updated_count = 0

        for bien_id, numero_piece in rows:

            existing = (
                db.query(GlpiAsset)
                .filter(GlpiAsset.bien_id == bien_id)
                .first()
            )

            if existing:

                existing.numero_piece = numero_piece
                existing.glpi_type = glpi_type
                existing.import_id = glpi_import.id
                existing.updated_at = datetime.now(UTC)

                updated_count += 1

            else:

                db.add(
                    GlpiAsset(
                        bien_id=bien_id,
                        numero_piece=numero_piece,
                        glpi_type=glpi_type,
                        import_id=glpi_import.id,
                        updated_at=datetime.now(UTC)
                    )
                )

                added_count += 1

        glpi_import.added_count = added_count
        glpi_import.updated_count = updated_count

        db.commit()

        return glpi_import

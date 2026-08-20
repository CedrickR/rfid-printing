import csv
from datetime import UTC, datetime
from io import StringIO

from app.models.bureau_model import BureauImport, BureauMapping

NIVEAU_COLUMN = "niveau"
NOM_PIECE_COLUMN = "nom_piece"
CODE_PIECE_SERVICE_COLUMN = "code_piece_service"
NOMBRE_POSTE_PREVU_COLUMN = "nombre_poste_prevu"
REQUIRED_COLUMNS = [
    NIVEAU_COLUMN,
    NOM_PIECE_COLUMN,
    CODE_PIECE_SERVICE_COLUMN,
    NOMBRE_POSTE_PREVU_COLUMN
]


class InvalidEncodingError(Exception):
    pass


class MissingColumnsError(Exception):
    def __init__(self, missing_columns):
        self.missing_columns = missing_columns


class DuplicateCodePieceServiceError(Exception):
    def __init__(self, duplicated_codes):
        self.duplicated_codes = duplicated_codes


class BureauImportService:
    """
    Import du fichier CSV de correspondance bureaux (';', avec
    en-tête, colonnes niveau/nom_piece/code_piece_service/
    nombre_poste_prevu), pour la colonne "Bureau" de l'inventaire
    (jointure entre code_piece_service et `Asset.local_numero`) et
    pour la répartition ordinateurs/écrans par bureau du tableau de
    bord.
    """

    @staticmethod
    def parse(content: bytes):
        """
        Décode et parse le CSV. Retourne une liste de (niveau,
        nom_piece, code_piece_service, nombre_poste_prevu).
        nombre_poste_prevu est ramené à un entier (0 si vide ou non
        numérique, plutôt que de faire échouer l'import).
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

            niveau = (row.get(NIVEAU_COLUMN) or "").strip()
            nom_piece = (row.get(NOM_PIECE_COLUMN) or "").strip()
            code_piece_service = (
                row.get(CODE_PIECE_SERVICE_COLUMN) or ""
            ).strip()

            try:
                nombre_poste_prevu = int(
                    (row.get(NOMBRE_POSTE_PREVU_COLUMN) or "0").strip()
                )
            except ValueError:
                nombre_poste_prevu = 0

            if not code_piece_service:
                continue

            if code_piece_service in seen_codes:
                duplicated_codes.append(code_piece_service)
                continue

            seen_codes.add(code_piece_service)

            rows.append(
                (niveau, nom_piece, code_piece_service, nombre_poste_prevu)
            )

        if duplicated_codes:
            raise DuplicateCodePieceServiceError(duplicated_codes)

        return rows

    @staticmethod
    def commit(db, rows, filename: str, username: str) -> BureauImport:
        """
        Ajoute les nouveaux codes pièce et met à jour ceux déjà connus
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

        for niveau, nom_piece, code_piece_service, nombre_poste_prevu in rows:

            existing = (
                db.query(BureauMapping)
                .filter(
                    BureauMapping.code_piece_service == code_piece_service
                )
                .first()
            )

            if existing:

                existing.niveau = niveau
                existing.nom_piece = nom_piece
                existing.nombre_poste_prevu = nombre_poste_prevu
                existing.import_id = bureau_import.id
                existing.updated_at = datetime.now(UTC)

                updated_count += 1

            else:

                db.add(
                    BureauMapping(
                        code_piece_service=code_piece_service,
                        niveau=niveau,
                        nom_piece=nom_piece,
                        nombre_poste_prevu=nombre_poste_prevu,
                        import_id=bureau_import.id,
                        updated_at=datetime.now(UTC)
                    )
                )

                added_count += 1

        bureau_import.added_count = added_count
        bureau_import.updated_count = updated_count

        db.commit()

        return bureau_import

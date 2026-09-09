import csv
from datetime import UTC, datetime
from io import StringIO

from app.models.asset_model import Asset
from app.models.destination_model import Destination
from app.models.destination_bureau_import_model import DestinationBureauImport

BIEN_ID_COLUMN = "numero"
DESTINATION_COLUMN = "Destination"
CODE_PIECE_SERVICE_COLUMN = "Codes pièces et niveau"
REQUIRED_COLUMNS = [
    BIEN_ID_COLUMN,
    DESTINATION_COLUMN,
    CODE_PIECE_SERVICE_COLUMN
]


class InvalidEncodingError(Exception):
    pass


class MissingColumnsError(Exception):
    def __init__(self, missing_columns):
        self.missing_columns = missing_columns


class DuplicateBienIdError(Exception):
    def __init__(self, duplicated_ids):
        self.duplicated_ids = duplicated_ids


class DestinationBureauImportService:
    """
    Import du fichier CSV de mise à jour Destination/Bureau (';', avec
    en-tête), keyé par Bien ID ("numero") plutôt que par code pièce
    (contrairement à l'import Bureaux existant, §2.12). Pour chaque
    bien déjà connu de l'inventaire, met à jour :

    - Destination (`Asset.destination`), avec ajout automatique à la
      liste des destinations connues (§2.12) si le libellé du fichier
      n'y figure pas encore ;
    - Bureau, via `Asset.local_numero` (comparé au `code_piece_service`
      des bureaux connus pour l'affichage, comme l'affectation
      manuelle depuis l'Inventaire).

    Ne touche jamais la colonne Utilisateur (absente de ce fichier).
    Une valeur vide dans le fichier efface la valeur existante (le
    fichier fait foi, comme l'import inventaire principal). Les Bien
    ID du fichier absents de l'inventaire sont ignorés (comptés à
    part, pas d'erreur).
    """

    @staticmethod
    def parse(content: bytes):
        """
        Décode et parse le CSV. Retourne une liste de (bien_id,
        destination, code_piece_service). Lève DuplicateBienIdError si
        le fichier contient plusieurs fois le même Bien ID.
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
            destination = (row.get(DESTINATION_COLUMN) or "").strip()
            code_piece_service = (
                row.get(CODE_PIECE_SERVICE_COLUMN) or ""
            ).strip()

            if not bien_id:
                continue

            if bien_id in seen_ids:
                duplicated_ids.append(bien_id)
                continue

            seen_ids.add(bien_id)

            rows.append((bien_id, destination, code_piece_service))

        if duplicated_ids:
            raise DuplicateBienIdError(duplicated_ids)

        return rows

    @staticmethod
    def commit(db, rows, filename: str, username: str) -> DestinationBureauImport:
        """
        Applique les lignes aux biens déjà connus de l'inventaire
        (ceux du fichier absents de l'inventaire sont ignorés).
        """

        import_row = DestinationBureauImport(
            filename=filename,
            imported_by=username,
            imported_at=datetime.now(UTC),
            total_rows=len(rows)
        )

        db.add(import_row)
        db.commit()
        db.refresh(import_row)

        known_destinations = {
            destination.libelle
            for destination in db.query(Destination).all()
        }

        updated_count = 0
        unmatched_count = 0

        for bien_id, destination, code_piece_service in rows:

            asset = (
                db.query(Asset)
                .filter(Asset.bien_id == bien_id)
                .first()
            )

            if not asset:
                unmatched_count += 1
                continue

            asset.destination = destination or None
            asset.local_numero = code_piece_service or None

            if destination and destination not in known_destinations:
                db.add(Destination(libelle=destination))
                known_destinations.add(destination)

            updated_count += 1

        import_row.updated_count = updated_count
        import_row.unmatched_count = unmatched_count

        db.commit()

        return import_row

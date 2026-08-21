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

# Colonnes supplémentaires affichées dans le tableau des écarts,
# récupérées si présentes dans le fichier GLPI sans faire échouer
# l'import si elles sont absentes (variantes d'export possibles).
LIEU_COLUMN = "Lieu"
STATUT_COLUMN = "Statut"
UTILISATEUR_COLUMN = "Utilisateur"
NUMERO_SERIE_COLUMN = "Numéro de série"

# Le numéro de la pièce est toujours sur 8 caractères dans l'inventaire
# (ex. "00600001") ; GLPI l'exporte parfois sans les zéros non
# significatifs (ex. "600001") : on complète à gauche pour rester
# comparable au numéro local de l'inventaire.
NUMERO_PIECE_LENGTH = 8


def pad_numero_piece(numero_piece: str) -> str:

    if not numero_piece:
        return numero_piece

    return numero_piece.zfill(NUMERO_PIECE_LENGTH)


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
    Import des exports GLPI (';', avec en-tête). Colonnes conservées :
    "Numéro d'inventaire" (Bien ID) et "Numéro de la pièce" (pour
    comparaison avec le numéro local déjà connu dans l'inventaire), et
    "Lieu"/"Statut"/"Utilisateur"/"Numéro de série" (informations
    complémentaires affichées dans le tableau des écarts et, pour
    "Utilisateur"/"Numéro de série", dans les colonnes correspondantes
    de l'Inventaire, sans effet sur la comparaison).
    """

    @staticmethod
    def parse_allow_duplicates(content: bytes):
        """
        Décode et parse le CSV. Retourne la liste complète de (bien_id,
        numero_piece, lieu, statut, utilisateur, numero_serie), une
        ligne par ligne du fichier (bien_id non vide), y compris les
        éventuels doublons de Bien ID : ne lève jamais
        DuplicateBienIdError, pour permettre leur correction en ligne
        avant import (voir find_duplicate_indices).
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

        for row in reader:

            bien_id = (row.get(BIEN_ID_COLUMN) or "").strip()
            numero_piece = pad_numero_piece(
                (row.get(NUMERO_PIECE_COLUMN) or "").strip()
            )
            lieu = (row.get(LIEU_COLUMN) or "").strip()
            statut = (row.get(STATUT_COLUMN) or "").strip()
            utilisateur = (row.get(UTILISATEUR_COLUMN) or "").strip()
            numero_serie = (row.get(NUMERO_SERIE_COLUMN) or "").strip()

            if not bien_id:
                continue

            rows.append(
                (bien_id, numero_piece, lieu, statut, utilisateur, numero_serie)
            )

        return rows

    @staticmethod
    def find_duplicate_indices(rows):
        """
        Retourne un dict {bien_id: [indices]} pour chaque Bien ID
        apparaissant plusieurs fois dans rows (indices dans la liste
        rows de toutes ses occurrences, pas seulement la 2e et plus).
        """

        indices_by_bien_id = {}

        for index, row in enumerate(rows):
            indices_by_bien_id.setdefault(row[0], []).append(index)

        return {
            bien_id: indices
            for bien_id, indices in indices_by_bien_id.items()
            if len(indices) > 1
        }

    @staticmethod
    def serialize_rows(rows) -> bytes:
        """
        Sérialise une liste de (bien_id, numero_piece, lieu, statut,
        utilisateur, numero_serie) en CSV (';', avec en-tête), pour
        pouvoir la redécoder plus tard via parse_allow_duplicates.
        Utilisé pour faire transiter l'état courant d'une correction de
        doublons entre deux requêtes (champ caché du formulaire), sans
        stockage côté serveur.
        """

        buffer = StringIO()

        writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

        writer.writerow([
            BIEN_ID_COLUMN,
            NUMERO_PIECE_COLUMN,
            LIEU_COLUMN,
            STATUT_COLUMN,
            UTILISATEUR_COLUMN,
            NUMERO_SERIE_COLUMN
        ])

        for row in rows:
            writer.writerow(list(row))

        return buffer.getvalue().encode("utf-8")

    @staticmethod
    def parse(content: bytes):
        """
        Décode et parse le CSV. Retourne une liste de (bien_id,
        numero_piece, lieu, statut, utilisateur, numero_serie). Lève
        DuplicateBienIdError si le fichier contient plusieurs fois le
        même Bien ID (cohérent avec l'import inventaire : on force un
        fichier propre plutôt que de choisir silencieusement une
        occurrence).
        """

        rows = GlpiImportService.parse_allow_duplicates(content)

        duplicates = GlpiImportService.find_duplicate_indices(rows)

        if duplicates:
            raise DuplicateBienIdError(list(duplicates.keys()))

        return rows

    @staticmethod
    def commit(db, rows, glpi_type: str, filename: str, username: str) -> GlpiImport:
        """
        Ajoute les nouveaux Bien ID et met à jour les biens déjà connus
        (jamais de doublon en base).
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

        for bien_id, numero_piece, lieu, statut, utilisateur, numero_serie in rows:

            existing = (
                db.query(GlpiAsset)
                .filter(GlpiAsset.bien_id == bien_id)
                .first()
            )

            if existing:

                existing.numero_piece = numero_piece
                existing.lieu = lieu
                existing.statut = statut
                existing.utilisateur = utilisateur
                existing.numero_serie = numero_serie
                existing.glpi_type = glpi_type
                existing.import_id = glpi_import.id
                existing.updated_at = datetime.now(UTC)

                updated_count += 1

            else:

                db.add(
                    GlpiAsset(
                        bien_id=bien_id,
                        numero_piece=numero_piece,
                        lieu=lieu,
                        statut=statut,
                        utilisateur=utilisateur,
                        numero_serie=numero_serie,
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

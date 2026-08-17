import csv
from datetime import UTC, datetime
from io import StringIO

from app.models.rfid_scan_model import RfidScanFile, RfidScanLine

LIEU_PREFIX = "L261"
BIEN_PREFIX = "261"


class InvalidEncodingError(Exception):
    pass


class NoValidLineError(Exception):
    """Aucune ligne exploitable dans le fichier (préfixes attendus absents)."""
    pass


def parse_lieu_code(raw: str) -> str | None:
    """Extrait le numéro de lieu d'un code "L261XXXXXXXX", ou None si le
    préfixe attendu est absent."""

    raw = (raw or "").strip()

    if not raw.startswith(LIEU_PREFIX):
        return None

    return raw[len(LIEU_PREFIX):]


def parse_bien_code(raw: str) -> str | None:
    """Extrait le Bien ID d'un code "261XXXXXXXX", ou None si le préfixe
    attendu est absent."""

    raw = (raw or "").strip()

    if not raw.startswith(BIEN_PREFIX):
        return None

    return raw[len(BIEN_PREFIX):]


def format_lieu_code(lieu_numero: str) -> str:
    return f"{LIEU_PREFIX}{lieu_numero}"


def format_bien_code(bien_id: str) -> str:
    return f"{BIEN_PREFIX}{bien_id}"


class RfidScanService:
    """
    Chargement, édition et export des fichiers CSV bruts issus d'un
    lecteur RFID : 2 colonnes sans en-tête, séparateur ';'
    (colonne 1 = "L261" + numéro de lieu, colonne 2 = "261" + Bien ID).
    """

    @staticmethod
    def parse(content: bytes):
        """
        Décode et parse le CSV. Retourne (lignes_valides, nb_lignes_invalides)
        où lignes_valides est une liste de (lieu_numero, bien_id).
        Les lignes dont l'une des deux colonnes ne respecte pas le
        préfixe attendu sont écartées et comptées, sans faire échouer
        l'ensemble de l'import (cohérent avec l'import inventaire).
        """

        try:
            raw_text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise InvalidEncodingError()

        reader = csv.reader(StringIO(raw_text), delimiter=";")

        # bien_id -> lieu_numero : un lecteur RFID peut relire la même
        # étiquette plusieurs fois dans une même passe (contrairement à
        # un export administratif où un doublon signale une erreur) ;
        # on ne conserve que la dernière lecture au lieu de faire
        # échouer l'import.
        seen = {}
        invalid_rows = 0

        for row in reader:

            if not row or all(not cell.strip() for cell in row):
                continue

            if len(row) < 2:
                invalid_rows += 1
                continue

            lieu_numero = parse_lieu_code(row[0])
            bien_id = parse_bien_code(row[1])

            if lieu_numero is None or bien_id is None or not lieu_numero or not bien_id:
                invalid_rows += 1
                continue

            seen[bien_id] = lieu_numero

        valid_lines = [
            (lieu_numero, bien_id)
            for bien_id, lieu_numero in seen.items()
        ]

        if not valid_lines:
            raise NoValidLineError()

        return valid_lines, invalid_rows

    @staticmethod
    def commit(db, valid_lines, filename: str, username: str):
        """
        Un Bien ID déjà présent en base (chargé via un fichier
        précédent) est mis à jour avec son nouveau numéro de lieu au
        lieu d'être dupliqué — le bien vient d'être relu, à un autre
        endroit. Retourne (scan_file, added_count, updated_count).
        """

        scan_file = RfidScanFile(
            filename=filename,
            imported_by=username,
            imported_at=datetime.now(UTC)
        )

        db.add(scan_file)
        db.commit()
        db.refresh(scan_file)

        added_count = 0
        updated_count = 0

        for lieu_numero, bien_id in valid_lines:

            existing = (
                db.query(RfidScanLine)
                .filter(RfidScanLine.bien_id == bien_id)
                .first()
            )

            if existing:

                existing.lieu_numero = lieu_numero
                existing.scan_file_id = scan_file.id

                updated_count += 1

            else:

                db.add(
                    RfidScanLine(
                        scan_file_id=scan_file.id,
                        lieu_numero=lieu_numero,
                        bien_id=bien_id
                    )
                )

                added_count += 1

        db.commit()

        return scan_file, added_count, updated_count

    @staticmethod
    def export_csv(lines) -> str:
        """
        Reconstruit le CSV 2 colonnes/';'/sans en-tête à partir des
        lignes (édités ou non).
        """

        buffer = StringIO()

        writer = csv.writer(buffer, delimiter=";", lineterminator="\n")

        for line in lines:
            writer.writerow(
                [
                    format_lieu_code(line.lieu_numero),
                    format_bien_code(line.bien_id)
                ]
            )

        return buffer.getvalue()

    @staticmethod
    def export_filename() -> str:

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

        return f"export_rfid_{timestamp}.csv"

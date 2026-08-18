import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

BASE_DIR = Path(__file__).resolve().parent.parent.parent

MAX_BACKUPS = 2

# Origine possible d'une sauvegarde : import CSV (déclenché
# automatiquement) ou action manuelle depuis la page de gestion.
BACKUP_SOURCES = {
    "import_inventaire": "Import inventaire",
    "import_rfid_scan": "Import scan RFID",
    "import_glpi": "Import GLPI",
    "manuel": "Sauvegarde manuelle"
}


class BackupNotFoundError(Exception):
    pass


class BackupService:
    """
    Sauvegarde/restauration du fichier SQLite actif. Le chemin de la
    base et son dossier de sauvegardes sont déduits de la session
    fournie (`db.get_bind()`) plutôt que d'une constante globale, pour
    que les tests (qui pointent vers une base SQLite distincte via
    dependency override) sauvegardent bien leur propre fichier et non
    la base de développement.

    Les métadonnées de chaque sauvegarde (date, auteur, origine,
    taille) sont stockées dans un fichier .json à côté du .db plutôt
    que dans une table de la base elle-même : cela évite qu'une
    restauration ne réécrive (et ne perde) l'historique des
    sauvegardes en même temps que le reste des données.
    """

    @staticmethod
    def _db_path(db: Session) -> Path:

        engine = db.get_bind()

        return Path(engine.url.database).resolve()

    @staticmethod
    def _backup_dir(db: Session) -> Path:

        return BASE_DIR / "backups" / BackupService._db_path(db).stem

    @staticmethod
    def _metadata_path(backup_dir: Path, filename: str) -> Path:

        return backup_dir / (Path(filename).stem + ".json")

    @staticmethod
    def create_backup(db: Session, source: str, created_by: str) -> dict:
        """
        Copie la base active vers un fichier horodaté (API backup de
        sqlite3, sûre même avec des écritures concurrentes), écrit ses
        métadonnées à côté, puis ne conserve que les MAX_BACKUPS
        sauvegardes les plus récentes.
        """

        backup_dir = BackupService._backup_dir(db)
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S_%f")
        filename = f"backup_{timestamp}.db"
        destination = backup_dir / filename

        source_conn = sqlite3.connect(str(BackupService._db_path(db)))
        dest_conn = sqlite3.connect(str(destination))

        try:
            with dest_conn:
                source_conn.backup(dest_conn)
        finally:
            source_conn.close()
            dest_conn.close()

        metadata = {
            "filename": filename,
            "created_at": datetime.now(UTC).isoformat(),
            "created_by": created_by,
            "source": source,
            "size_bytes": destination.stat().st_size
        }

        BackupService._metadata_path(backup_dir, filename).write_text(
            json.dumps(metadata),
            encoding="utf-8"
        )

        BackupService._enforce_retention(db)

        return metadata

    @staticmethod
    def _enforce_retention(db: Session):

        backups = BackupService.list_backups(db)

        for old in backups[MAX_BACKUPS:]:
            BackupService._delete_files(db, old["filename"])

    @staticmethod
    def _delete_files(db: Session, filename: str):

        backup_dir = BackupService._backup_dir(db)

        db_path = backup_dir / filename
        meta_path = BackupService._metadata_path(backup_dir, filename)

        if db_path.exists():
            db_path.unlink()

        if meta_path.exists():
            meta_path.unlink()

    @staticmethod
    def list_backups(db: Session) -> list:
        """
        Sauvegardes disponibles, les plus récentes en premier.
        """

        backup_dir = BackupService._backup_dir(db)

        if not backup_dir.exists():
            return []

        backups = []

        for meta_file in backup_dir.glob("*.json"):

            try:
                metadata = json.loads(meta_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue

            if not (backup_dir / metadata.get("filename", "")).exists():
                continue

            backups.append(metadata)

        backups.sort(key=lambda b: b["created_at"], reverse=True)

        return backups

    @staticmethod
    def get_backup(db: Session, filename: str) -> dict:

        for backup in BackupService.list_backups(db):
            if backup["filename"] == filename:
                return backup

        raise BackupNotFoundError()

    @staticmethod
    def delete_backup(db: Session, filename: str):

        BackupService.get_backup(db, filename)
        BackupService._delete_files(db, filename)

    @staticmethod
    def restore_backup(db: Session, filename: str) -> dict:
        """
        Remplace le fichier de base active par le contenu de la
        sauvegarde choisie. Ferme le pool de connexions SQLAlchemy
        avant le remplacement pour que les requêtes suivantes ouvrent
        une connexion fraîche vers la base restaurée.
        """

        backup = BackupService.get_backup(db, filename)
        backup_path = BackupService._backup_dir(db) / filename
        db_path = BackupService._db_path(db)

        engine = db.get_bind()

        db.close()
        engine.dispose()

        tmp_path = db_path.with_suffix(".restoring")
        shutil.copy2(backup_path, tmp_path)
        os.replace(tmp_path, db_path)

        return backup

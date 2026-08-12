from datetime import UTC, datetime

from app.models.asset_model import Asset
from app.models.print_history_model import PrintHistory
from app.models.print_job_line_model import PrintJobLine

from app.services.cmd_generator import CommandGenerator
from app.services.reprint_service import ReprintService


class EmptyPrintJobError(Exception):
    pass


class AlreadyGeneratedError(Exception):
    pass


class PrintJobService:
    """
    Génération du fichier CMD d'un lot, partagée entre l'API (print_router)
    et l'UI Jinja2 (web_router) pour éviter la double implémentation.
    """

    @staticmethod
    def generate(db, job, username: str, generator=None) -> str:

        lines = (
            db.query(PrintJobLine)
            .filter(PrintJobLine.job_id == job.id)
            .all()
        )

        if not lines:
            raise EmptyPrintJobError()

        if ReprintService.has_generated_before(db, job.id):
            raise AlreadyGeneratedError()

        assets = []

        for line in lines:

            asset = (
                db.query(Asset)
                .filter(Asset.id == line.asset_id)
                .first()
            )

            if asset:
                assets.append(asset)

        generator = generator or CommandGenerator()

        filename = generator.generate(
            job_id=job.id,
            assets=assets
        )

        job.generated_file = filename
        job.generated_at = datetime.now(UTC)
        job.status = "GENERATED"

        history = PrintHistory(
            job_id=job.id,
            username=username,
            action="GENERATED",
            file_name=filename,
            labels_count=job.labels_count
        )

        db.add(history)

        db.commit()
        db.refresh(job)

        return filename

from app.models.print_history_model import PrintHistory


class ReprintService:

    @staticmethod
    def register_reprint(
        db,
        job,
        username
    ):

        if job is None:
            raise ValueError(
                "Le lot est introuvable"
            )

        history = PrintHistory(
            job_id=job.id,
            username=username,
            action="REPRINTED",
            file_name=job.generated_file,
            labels_count=job.labels_count
        )

        db.add(history)

        db.commit()

        return history

    @staticmethod
    def has_generated_before(
        db,
        job_id
    ):

        return (
            db.query(PrintHistory)
            .filter(
                PrintHistory.job_id == job_id,
                PrintHistory.action == "GENERATED"
            )
            .first()
            is not None
        )
from datetime import UTC, datetime

from app.models.cmd_template_model import CmdTemplate
from app.services.cmd_generator import (
    DEFAULT_HEADER_TEMPLATE,
    DEFAULT_LINE_TEMPLATE,
)


class CmdTemplateService:
    """
    Gère le gabarit (unique, modifiable) utilisé pour générer les
    fichiers .cmd. Aucune ligne en base au premier démarrage : la
    version par défaut (celle du format historique) fait foi tant que
    personne ne l'a personnalisée.
    """

    @staticmethod
    def get_current(db) -> CmdTemplate:

        template = (
            db.query(CmdTemplate)
            .order_by(CmdTemplate.id.desc())
            .first()
        )

        if template is None:

            template = CmdTemplate(
                header_template=DEFAULT_HEADER_TEMPLATE,
                line_template=DEFAULT_LINE_TEMPLATE,
                updated_by="system",
                updated_at=datetime.now(UTC)
            )

        return template

    @staticmethod
    def update(db, header_template: str, line_template: str, username: str) -> CmdTemplate:

        template = CmdTemplate(
            header_template=header_template,
            line_template=line_template,
            updated_by=username,
            updated_at=datetime.now(UTC)
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        return template

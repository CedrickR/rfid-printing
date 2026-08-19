from sqlalchemy.orm import Session

from app.models.destination_model import Destination


class DuplicateDestinationError(Exception):
    pass


class InvalidDestinationError(Exception):
    pass


class DestinationNotFoundError(Exception):
    pass


class DestinationService:
    """
    Gestion de la liste des destinations possibles (colonne
    "Destination" de l'inventaire). Une destination est une simple
    valeur de liste : la supprimer n'efface pas la valeur déjà
    affectée aux biens qui l'utilisaient.
    """

    @staticmethod
    def list_destinations(db: Session):

        return (
            db.query(Destination)
            .order_by(Destination.libelle)
            .all()
        )

    @staticmethod
    def _check_no_duplicate(db: Session, libelle: str, exclude_id: int = None):

        query = db.query(Destination).filter(Destination.libelle == libelle)

        if exclude_id is not None:
            query = query.filter(Destination.id != exclude_id)

        if query.first():
            raise DuplicateDestinationError()

    @staticmethod
    def create_destination(db: Session, libelle: str) -> Destination:

        libelle = (libelle or "").strip()

        if not libelle:
            raise InvalidDestinationError()

        DestinationService._check_no_duplicate(db, libelle)

        destination = Destination(libelle=libelle)

        db.add(destination)
        db.commit()
        db.refresh(destination)

        return destination

    @staticmethod
    def update_destination(
        db: Session, destination_id: int, libelle: str
    ) -> Destination:

        destination = (
            db.query(Destination)
            .filter(Destination.id == destination_id)
            .first()
        )

        if not destination:
            raise DestinationNotFoundError()

        libelle = (libelle or "").strip()

        if not libelle:
            raise InvalidDestinationError()

        DestinationService._check_no_duplicate(
            db, libelle, exclude_id=destination_id
        )

        destination.libelle = libelle

        db.commit()

        return destination

    @staticmethod
    def delete_destination(db: Session, destination_id: int):

        destination = (
            db.query(Destination)
            .filter(Destination.id == destination_id)
            .first()
        )

        if not destination:
            raise DestinationNotFoundError()

        db.delete(destination)
        db.commit()

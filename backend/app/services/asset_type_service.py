from sqlalchemy.orm import Session

from app.models.asset_type_model import AssetType


class DuplicateAssetTypeError(Exception):
    pass


class InvalidAssetTypeError(Exception):
    pass


class AssetTypeNotFoundError(Exception):
    pass


class AssetTypeService:
    """
    Gestion de la liste des types de bien possibles (colonne "Type de
    bien" de l'inventaire). Un type de bien est une simple valeur de
    liste : la supprimer n'efface pas la valeur déjà affectée aux
    biens qui l'utilisaient.
    """

    @staticmethod
    def list_asset_types(db: Session):

        return (
            db.query(AssetType)
            .order_by(AssetType.libelle)
            .all()
        )

    @staticmethod
    def _check_no_duplicate(db: Session, libelle: str, exclude_id: int = None):

        query = db.query(AssetType).filter(AssetType.libelle == libelle)

        if exclude_id is not None:
            query = query.filter(AssetType.id != exclude_id)

        if query.first():
            raise DuplicateAssetTypeError()

    @staticmethod
    def create_asset_type(db: Session, libelle: str) -> AssetType:

        libelle = (libelle or "").strip()

        if not libelle:
            raise InvalidAssetTypeError()

        AssetTypeService._check_no_duplicate(db, libelle)

        asset_type = AssetType(libelle=libelle)

        db.add(asset_type)
        db.commit()
        db.refresh(asset_type)

        return asset_type

    @staticmethod
    def update_asset_type(
        db: Session, asset_type_id: int, libelle: str
    ) -> AssetType:

        asset_type = (
            db.query(AssetType)
            .filter(AssetType.id == asset_type_id)
            .first()
        )

        if not asset_type:
            raise AssetTypeNotFoundError()

        libelle = (libelle or "").strip()

        if not libelle:
            raise InvalidAssetTypeError()

        AssetTypeService._check_no_duplicate(
            db, libelle, exclude_id=asset_type_id
        )

        asset_type.libelle = libelle

        db.commit()

        return asset_type

    @staticmethod
    def delete_asset_type(db: Session, asset_type_id: int):

        asset_type = (
            db.query(AssetType)
            .filter(AssetType.id == asset_type_id)
            .first()
        )

        if not asset_type:
            raise AssetTypeNotFoundError()

        db.delete(asset_type)
        db.commit()

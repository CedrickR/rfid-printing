from datetime import datetime
from datetime import UTC

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.asset_model import Asset
from app.models.inventory_check_line_model import InventoryCheckLine


STATUT_PRESENT = "Présent"
STATUT_ABSENT = "Absent"
STATUT_EN_TROP = "En Trop"

STATUTS = (STATUT_PRESENT, STATUT_ABSENT, STATUT_EN_TROP)


class InventoryCheckLineNotFoundError(Exception):
    pass


class NotExtraLineError(Exception):
    """
    Suppression demandée sur une ligne liée à un bien connu de
    l'inventaire (asset_id renseigné) : seules les lignes "en trop"
    (ajoutées manuellement) peuvent être supprimées, une ligne liée à
    un bien connu étant de toute façon recréée automatiquement au
    prochain affichage du local tant que le bien y reste affecté.
    """
    pass


class NotTemporaryBienIdError(Exception):
    """
    Rattachement à un Bien ID demandé sur une ligne qui n'est pas en
    attente de rattachement (bien_id_temporaire=False) : soit déjà
    liée à un bien connu, soit déjà pourvue de son vrai Bien ID.
    """
    pass


class BienIdRequiredError(Exception):
    pass


class AssetAlreadyTrackedInLocalError(Exception):
    """
    Rattachement demandé vers un Bien ID déjà suivi (ligne connue,
    asset_id renseigné) dans ce même local : ce bien a déjà sa propre
    ligne, le rattacher créerait un doublon pour le même bien dans le
    même local.
    """
    pass


class InventoryCheckService:
    """
    Suivi de l'inventaire par local (§2.13) : pour un local donné, une
    ligne par bien actif qui y est actuellement affecté (créée à la
    demande lors du premier affichage du local pour ce bien), plus les
    lignes "en trop" ajoutées manuellement (biens physiquement
    présents mais non affectés à ce local dans l'inventaire, ou
    inconnus).
    """

    @staticmethod
    def list_lines_for_local(db: Session, local_libelle: str):
        """
        Renvoie les lignes du local demandé, en créant d'abord (le cas
        échéant) une ligne pour chaque bien actif actuellement affecté
        à ce local qui n'en a pas encore. Triées : biens connus par
        Bien ID, puis biens "en trop" par ordre d'ajout.
        """

        if not local_libelle:
            return []

        assets = (
            db.query(Asset)
            .filter(Asset.local_libelle == local_libelle)
            .filter(Asset.is_active.is_(True))
            .all()
        )

        existing_asset_ids = {
            line.asset_id
            for line in (
                db.query(InventoryCheckLine)
                .filter(InventoryCheckLine.local_libelle == local_libelle)
                .filter(InventoryCheckLine.asset_id.isnot(None))
                .all()
            )
        }

        created = False

        for asset in assets:

            if asset.id in existing_asset_ids:
                continue

            db.add(
                InventoryCheckLine(
                    local_libelle=local_libelle,
                    asset_id=asset.id,
                    statut=STATUT_PRESENT,
                    updated_by="system",
                    updated_at=datetime.now(UTC)
                )
            )

            created = True

        if created:
            db.commit()

        known_lines = (
            db.query(InventoryCheckLine)
            .join(Asset, InventoryCheckLine.asset_id == Asset.id)
            .filter(InventoryCheckLine.local_libelle == local_libelle)
            .order_by(Asset.bien_id)
            .all()
        )

        extra_lines = (
            db.query(InventoryCheckLine)
            .filter(InventoryCheckLine.local_libelle == local_libelle)
            .filter(InventoryCheckLine.asset_id.is_(None))
            .order_by(InventoryCheckLine.id)
            .all()
        )

        return known_lines + extra_lines

    @staticmethod
    def list_lines_by_statut(db: Session, statut: str):
        """
        Renvoie toutes les lignes existantes (tous locaux confondus)
        ayant ce statut, sans en créer de nouvelle — contrairement à
        list_lines_for_local, une ligne "Absent"/"En Trop" n'existe
        que si un utilisateur l'a explicitement enregistrée (le statut
        par défaut à la création est toujours "Présent"). Triées par
        local, puis Bien ID pour les biens connus.
        """

        return (
            db.query(InventoryCheckLine)
            .filter(InventoryCheckLine.statut == statut)
            .order_by(InventoryCheckLine.local_libelle, InventoryCheckLine.id)
            .all()
        )

    @staticmethod
    def list_en_trop_lines(db: Session):
        """
        Tous les biens "en trop" à traiter (tous locaux confondus) :
        les lignes taguées "en trop" (ajoutées manuellement via
        add_extra_line, asset_id NULL) quel que soit leur statut
        actuel — un bien en trop reste à traiter dans le logiciel de
        gestion d'inventaire externe tant qu'il n'y est pas reporté,
        indépendamment de son statut de présence lors du contrôle —,
        plus les lignes de biens connus explicitement marquées au
        statut "En Trop". Triées par local.
        """

        return (
            db.query(InventoryCheckLine)
            .filter(
                or_(
                    InventoryCheckLine.asset_id.is_(None),
                    InventoryCheckLine.statut == STATUT_EN_TROP
                )
            )
            .order_by(InventoryCheckLine.local_libelle, InventoryCheckLine.id)
            .all()
        )

    @staticmethod
    def add_extra_line(
        db: Session,
        local_libelle: str,
        bien_id: str,
        designation: str,
        type_bien_id,
        commentaire: str,
        username: str
    ) -> InventoryCheckLine:
        """
        Ajoute un bien "en trop" : physiquement présent dans le local
        mais non affecté à celui-ci dans l'inventaire (ou inconnu).
        Statut toujours "Présent" à la création (le bien vient d'être
        constaté sur place) ; modifiable ensuite comme les autres
        lignes.

        Le Bien ID est facultatif : s'il n'est pas connu sur le
        terrain (ex. fauteuil non étiqueté), une référence temporaire
        "SN-<id>" est générée automatiquement (bien_id_temporaire=True)
        — à rattacher plus tard à son vrai Bien ID via
        attach_bien_id.
        """

        bien_id = (bien_id or "").strip()
        is_temporaire = not bien_id

        line = InventoryCheckLine(
            local_libelle=local_libelle,
            asset_id=None,
            bien_id=bien_id or None,
            bien_id_temporaire=is_temporaire,
            designation=(designation or "").strip() or None,
            type_bien_id=type_bien_id,
            commentaire=commentaire or None,
            statut=STATUT_PRESENT,
            updated_by=username,
            updated_at=datetime.now(UTC)
        )

        db.add(line)
        db.commit()
        db.refresh(line)

        if is_temporaire:
            line.bien_id = f"SN-{line.id}"
            db.commit()

        return line

    @staticmethod
    def update_line(
        db: Session,
        line_id: int,
        statut: str,
        commentaire: str,
        type_bien_id,
        username: str
    ) -> InventoryCheckLine:
        """
        Le type de bien d'une ligne liée à un bien connu (asset_id
        renseigné) n'est jamais stocké sur la ligne elle-même (voir
        InventoryCheckLine) : le modifier ici met à jour l'Asset lié,
        exactement comme depuis l'Inventaire (§2.4) — une seule valeur
        partagée entre les deux pages. Pour un bien "en trop", le type
        de bien est propre à la ligne.
        """

        line = (
            db.query(InventoryCheckLine)
            .filter(InventoryCheckLine.id == line_id)
            .first()
        )

        if not line:
            raise InventoryCheckLineNotFoundError()

        if line.asset_id is not None:

            asset = (
                db.query(Asset)
                .filter(Asset.id == line.asset_id)
                .first()
            )

            if asset:
                asset.type_bien_id = type_bien_id

        else:
            line.type_bien_id = type_bien_id

        line.statut = statut
        line.commentaire = commentaire or None
        line.updated_by = username
        line.updated_at = datetime.now(UTC)

        db.commit()

        return line

    @staticmethod
    def attach_bien_id(
        db: Session, line_id: int, bien_id: str, username: str
    ) -> InventoryCheckLine:
        """
        Rattache une ligne "sans numéro" (bien_id_temporaire=True,
        voir add_extra_line) à son vrai Bien ID, une fois celui-ci
        retrouvé sur le terrain ou dans le logiciel de gestion
        d'inventaire externe. Le commentaire et le statut de la ligne
        sont conservés (pas de recréation).

        - Si ce Bien ID correspond à un bien actif connu de
          l'inventaire, la ligne devient une ligne "normale" liée à
          cet Asset (asset_id renseigné, bien_id/designation/
          type_bien_id propres à la ligne effacés — Bien ID,
          désignation et type de bien sont alors lus en direct sur
          l'Asset, comme pour toute ligne connue).
        - Sinon, la référence temporaire est simplement remplacée par
          le Bien ID indiqué : la ligne reste un bien "en trop" (donc
          toujours à reporter dans le logiciel de gestion
          d'inventaire externe), mais n'est plus "sans numéro".
        """

        bien_id = (bien_id or "").strip()

        if not bien_id:
            raise BienIdRequiredError()

        line = (
            db.query(InventoryCheckLine)
            .filter(InventoryCheckLine.id == line_id)
            .first()
        )

        if not line:
            raise InventoryCheckLineNotFoundError()

        if not line.bien_id_temporaire:
            raise NotTemporaryBienIdError()

        asset = (
            db.query(Asset)
            .filter(Asset.bien_id == bien_id)
            .filter(Asset.is_active.is_(True))
            .first()
        )

        if asset:

            already_tracked = (
                db.query(InventoryCheckLine)
                .filter(InventoryCheckLine.local_libelle == line.local_libelle)
                .filter(InventoryCheckLine.asset_id == asset.id)
                .first()
            )

            if already_tracked:
                raise AssetAlreadyTrackedInLocalError()

            line.asset_id = asset.id
            line.bien_id = None
            line.designation = None
            line.type_bien_id = None
        else:
            line.bien_id = bien_id

        line.bien_id_temporaire = False
        line.updated_by = username
        line.updated_at = datetime.now(UTC)

        db.commit()

        return line

    @staticmethod
    def delete_extra_line(db: Session, line_id: int):

        line = (
            db.query(InventoryCheckLine)
            .filter(InventoryCheckLine.id == line_id)
            .first()
        )

        if not line:
            raise InventoryCheckLineNotFoundError()

        if line.asset_id is not None:
            raise NotExtraLineError()

        db.delete(line)
        db.commit()

    @staticmethod
    def validate_line(db: Session, line_id: int, username: str):
        """
        Valide une ligne depuis l'onglet "Biens à traiter" (§2.13),
        pour la faire disparaître des filtres Absent/En Trop :

        - Bien connu de l'inventaire : remis au statut "Présent"
          (retrouvé, ou anomalie levée) — modifiable de nouveau
          ensuite comme n'importe quelle ligne.
        - Bien "en trop" : la ligne est supprimée, l'anomalie étant
          considérée reportée dans le logiciel de gestion d'inventaire
          externe (elle n'a alors plus besoin d'être suivie ici).
        """

        line = (
            db.query(InventoryCheckLine)
            .filter(InventoryCheckLine.id == line_id)
            .first()
        )

        if not line:
            raise InventoryCheckLineNotFoundError()

        if line.asset_id is not None:

            line.statut = STATUT_PRESENT
            line.updated_by = username
            line.updated_at = datetime.now(UTC)

            db.commit()

        else:

            db.delete(line)
            db.commit()

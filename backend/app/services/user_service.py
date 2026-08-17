from app.auth import ROLES, ROLE_ADMIN, hash_password
from app.models.user_model import User

MIN_PASSWORD_LENGTH = 8


class DuplicateUsernameError(Exception):
    pass


class InvalidRoleError(Exception):
    pass


class WeakPasswordError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class LastAdminError(Exception):
    """Empêcherait de ne plus avoir aucun administrateur restant."""
    pass


class SelfDeleteError(Exception):
    pass


class UserService:

    @staticmethod
    def list_users(db):

        return (
            db.query(User)
            .order_by(User.username)
            .all()
        )

    @staticmethod
    def _count_admins(db, excluding_user_id=None):

        query = db.query(User).filter(User.role == ROLE_ADMIN)

        if excluding_user_id is not None:
            query = query.filter(User.id != excluding_user_id)

        return query.count()

    @staticmethod
    def create_user(db, username: str, password: str, role: str) -> User:

        username = (username or "").strip()

        if role not in ROLES:
            raise InvalidRoleError()

        if len(password or "") < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError()

        existing = (
            db.query(User)
            .filter(User.username == username)
            .first()
        )

        if not username or existing:
            raise DuplicateUsernameError()

        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def update_role(db, user_id: int, new_role: str) -> User:

        if new_role not in ROLES:
            raise InvalidRoleError()

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise UserNotFoundError()

        if (
            user.role == ROLE_ADMIN
            and new_role != ROLE_ADMIN
            and UserService._count_admins(db, excluding_user_id=user.id) == 0
        ):
            raise LastAdminError()

        user.role = new_role

        db.commit()

        return user

    @staticmethod
    def reset_password(db, user_id: int, new_password: str) -> User:

        if len(new_password or "") < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError()

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise UserNotFoundError()

        user.password_hash = hash_password(new_password)

        db.commit()

        return user

    @staticmethod
    def delete_user(db, user_id: int, current_username: str):

        user = (
            db.query(User)
            .filter(User.id == user_id)
            .first()
        )

        if not user:
            raise UserNotFoundError()

        if user.username == current_username:
            raise SelfDeleteError()

        if (
            user.role == ROLE_ADMIN
            and UserService._count_admins(db, excluding_user_id=user.id) == 0
        ):
            raise LastAdminError()

        db.delete(user)

        db.commit()

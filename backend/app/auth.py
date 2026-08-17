import os
import secrets
import warnings

from datetime import datetime, timedelta, UTC

from jose import JWTError
from jose import jwt

from passlib.context import CryptContext

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi.security import HTTPBearer
from fastapi.security import HTTPAuthorizationCredentials

from app.models.user_model import User

security = HTTPBearer()

COOKIE_NAME = "access_token"


def _load_secret_key() -> str:

    env_key = os.environ.get("RFID_SECRET_KEY")

    if env_key:
        return env_key

    warnings.warn(
        "RFID_SECRET_KEY n'est pas défini : une clé aléatoire temporaire "
        "est utilisée pour cette exécution. Les jetons émis ne survivront "
        "pas à un redémarrage. Définissez RFID_SECRET_KEY en production.",
        stacklevel=2
    )

    return secrets.token_hex(32)


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(
        plain_password,
        hashed_password
):
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


def authenticate_user(db, username: str, password: str):

    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not user:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def create_access_token(data: dict):

    to_encode = data.copy()

    expire = datetime.now(UTC) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_token(token: str):

    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    except JWTError:
        return None


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    payload = decode_token(
        credentials.credentials
    )

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token invalide"
        )

    return payload


# Profils applicatifs : l'administrateur gère toutes les fonctions, le
# gestionnaire d'inventaire couvre l'usage courant (import, biens, lots,
# historique, fichiers RFID) sans les fonctions sensibles (modèle CMD,
# utilisateurs, réinitialisation de la base), et le lecteur n'a accès
# qu'à la consultation de l'inventaire.
ROLE_ADMIN = "administrateur"
ROLE_MANAGER = "gestionnaire"
ROLE_READER = "lecteur"

ROLES = (ROLE_ADMIN, ROLE_MANAGER, ROLE_READER)


def require_admin(user):

    if user["role"] != ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Accès refusé"
        )


def require_manager(user):

    if user["role"] not in (ROLE_ADMIN, ROLE_MANAGER):
        raise HTTPException(
            status_code=403,
            detail="Accès refusé"
        )


class WebAuthRequired(Exception):
    """
    Levée par get_current_user_web quand aucune session cookie valide
    n'est présente. Un handler dédié (voir main.py) la transforme en
    redirection vers /login, adaptée à une navigation par pages plutôt
    qu'à un client API.
    """

    def __init__(self, next_path: str = "/dashboard"):
        self.next_path = next_path


def get_current_user_web(request: Request):

    token = request.cookies.get(COOKIE_NAME)

    payload = decode_token(token) if token else None

    if not payload:
        raise WebAuthRequired(next_path=request.url.path)

    # Rendu disponible aux templates (base.html) sans devoir l'ajouter
    # au contexte de chaque route individuellement.
    request.state.role = payload.get("role")

    return payload


def set_auth_cookie(response, token: str):

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookie(response):

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
    )
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from fastapi.security import HTTPAuthorizationCredentials

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User

from app.auth import verify_password
from app.auth import create_access_token
from app.auth import decode_token

from app.schemas import LoginRequest

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

security = HTTPBearer()


@router.post("/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):

    user = (
        db.query(User)
        .filter(User.username == request.username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Utilisateur non trouvé"
        )

    if not verify_password(
        request.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Mot de passe invalide"
        )

    token = create_access_token(
        {
            "sub": user.username,
            "role": user.role
        }
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from fastapi.security import HTTPAuthorizationCredentials

security = HTTPBearer()


@router.get("/me")
def me(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    payload = decode_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Token invalide"
        )

    return payload


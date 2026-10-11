from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Потрібна автентифікація (заголовок Authorization: Bearer <токен>)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    error = HTTPException(
        status.HTTP_401_UNAUTHORIZED, "Недійсний або прострочений токен", headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode_token(token)
    except PyJWTError:
        raise error from None
    user = db.get(User, int(payload.get("sub", 0)))
    if not user:
        raise error from None
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Потрібні права адміністратора")
    return user

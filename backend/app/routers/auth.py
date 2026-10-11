from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, Token, UserCreate, UserOut
from ..security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Автентифікація"])


def _authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неправильний email або пароль")
    return user


@router.post("/register", response_model=UserOut, status_code=201, summary="Реєстрація співробітника")
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Користувач з таким email вже існує")
    user = User(
        email=data.email.lower(), password_hash=hash_password(data.password), full_name=data.full_name, role="manager"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token, summary="Вхід (JSON) — повертає JWT")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = _authenticate(db, data.email, data.password)
    return Token(access_token=create_token(user.id, user.role), user=UserOut.model_validate(user))


@router.post("/token", summary="Вхід (OAuth2 form) — для кнопки Authorize у Swagger")
def token(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = _authenticate(db, form.username, form.password)
    return {"access_token": create_token(user.id, user.role), "token_type": "bearer"}


@router.get("/me", response_model=UserOut, summary="Поточний користувач")
def me(user: User = Depends(get_current_user)):
    return user

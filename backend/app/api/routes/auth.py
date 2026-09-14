import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.models.phone_verification import VerificationPurpose
from app.models.user import User
from app.schemas.auth import (
    LoginConfirmRequest,
    PhoneRequest,
    RefreshRequest,
    RegisterConfirmRequest,
    TokenPair,
)
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens_for_user(user: User) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user.id, user.organization_id, user.role),
        refresh_token=create_refresh_token(user.id, user.organization_id),
    )


@router.post("/register/request-code", status_code=status.HTTP_204_NO_CONTENT)
def register_request_code(payload: PhoneRequest, db: Session = Depends(get_db)):
    if auth_service.get_user_by_phone(db, payload.phone):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с этим номером уже зарегистрирован, используйте вход",
        )
    try:
        auth_service.request_code(db, payload.phone, VerificationPurpose.register)
    except auth_service.RateLimitedError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))


@router.post("/register/confirm", response_model=TokenPair)
def register_confirm(payload: RegisterConfirmRequest, db: Session = Depends(get_db)):
    if auth_service.get_user_by_phone(db, payload.phone):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с этим номером уже зарегистрирован, используйте вход",
        )
    try:
        auth_service.verify_code(db, payload.phone, payload.code, VerificationPurpose.register)
    except (auth_service.InvalidCodeError, auth_service.CodeExpiredError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    user = auth_service.register_organization(
        db, payload.phone, payload.organization_name, payload.user_name
    )
    return _tokens_for_user(user)


@router.post("/login/request-code", status_code=status.HTTP_204_NO_CONTENT)
def login_request_code(payload: PhoneRequest, db: Session = Depends(get_db)):
    user = auth_service.get_user_by_phone(db, payload.phone)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с этим номером не найден, зарегистрируйте организацию",
        )
    try:
        auth_service.request_code(db, payload.phone, VerificationPurpose.login)
    except auth_service.RateLimitedError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc))


@router.post("/login/confirm", response_model=TokenPair)
def login_confirm(payload: LoginConfirmRequest, db: Session = Depends(get_db)):
    try:
        auth_service.verify_code(db, payload.phone, payload.code, VerificationPurpose.login)
    except (auth_service.InvalidCodeError, auth_service.CodeExpiredError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    user = auth_service.get_user_by_phone(db, payload.phone)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return _tokens_for_user(user)


@router.post("/refresh", response_model=TokenPair)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или истёкший refresh-токен",
        )
    if data.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется refresh-токен"
        )

    user = db.get(User, uuid.UUID(data["sub"]))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")
    return _tokens_for_user(user)

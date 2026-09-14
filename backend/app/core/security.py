"""JWT access/refresh токены для аутентификации по SMS-коду."""

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings
from app.models.user import UserRole

ALGORITHM = "HS256"


def create_access_token(user_id: uuid.UUID, organization_id: uuid.UUID, role: UserRole) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "organization_id": str(organization_id),
        "role": role.value,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID, organization_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "organization_id": str(organization_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Декодирует и валидирует JWT. Бросает ValueError при невалидном/истёкшем токене."""
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError(str(exc)) from exc

"""Бизнес-логика аутентификации по SMS-коду: выдача, проверка, антиабьюз."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.phone_verification import PhoneVerificationCode, VerificationPurpose
from app.models.subscription import Subscription, SubscriptionPlan, SubscriptionStatus
from app.models.user import User, UserRole
from app.services.sms import get_sms_sender

CODE_TTL_MINUTES = 5
CODE_LENGTH = 6
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60
# Дефолтный лимит машин на trial-подписке — разумный старт для ИП с 1–3
# машинами (основной сегмент MVP, см. память проекта), не блокирует typical
# пилотного клиента сразу при регистрации.
DEFAULT_TRIAL_VEHICLES_LIMIT = 3


class AuthError(Exception):
    """Базовая ошибка аутентификации с сообщением, пригодным для показа пользователю."""


class RateLimitedError(AuthError):
    pass


class InvalidCodeError(AuthError):
    pass


class CodeExpiredError(AuthError):
    pass


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"


def _last_code(db: Session, phone: str, purpose: VerificationPurpose) -> PhoneVerificationCode | None:
    return db.execute(
        select(PhoneVerificationCode)
        .where(
            PhoneVerificationCode.phone == phone,
            PhoneVerificationCode.purpose == purpose,
        )
        .order_by(PhoneVerificationCode.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def request_code(db: Session, phone: str, purpose: VerificationPurpose) -> None:
    """Генерирует и отправляет новый код, соблюдая cooldown на повторную отправку."""
    now = datetime.now(timezone.utc)
    last = _last_code(db, phone, purpose)
    if last is not None:
        created_at = last.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if (now - created_at).total_seconds() < RESEND_COOLDOWN_SECONDS:
            raise RateLimitedError(
                f"Повторную отправку кода можно запросить не чаще раза в {RESEND_COOLDOWN_SECONDS} секунд"
            )

    code = _generate_code()
    record = PhoneVerificationCode(
        phone=phone,
        code_hash=_hash_code(code),
        purpose=purpose,
        expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
    )
    db.add(record)
    db.commit()

    get_sms_sender().send(phone, code)


def verify_code(db: Session, phone: str, code: str, purpose: VerificationPurpose) -> None:
    """Проверяет код. Бросает InvalidCodeError/CodeExpiredError, если проверка не прошла."""
    record = _last_code(db, phone, purpose)
    if record is None or record.consumed_at is not None:
        raise InvalidCodeError("Код не запрашивался или уже был использован")

    if record.attempts >= MAX_ATTEMPTS:
        raise InvalidCodeError("Превышено количество попыток ввода кода, запросите новый")

    now = datetime.now(timezone.utc)
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        raise CodeExpiredError("Срок действия кода истёк, запросите новый")

    if record.code_hash != _hash_code(code):
        record.attempts += 1
        if record.attempts >= MAX_ATTEMPTS:
            record.consumed_at = now
        db.commit()
        raise InvalidCodeError("Неверный код подтверждения")

    record.consumed_at = now
    db.commit()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    return db.execute(select(User).where(User.phone == phone)).scalar_one_or_none()


def register_organization(db: Session, phone: str, organization_name: str, user_name: str) -> User:
    """Создаёт организацию и первого пользователя (owner) после подтверждения кода."""
    organization = Organization(name=organization_name)
    db.add(organization)
    db.flush()

    # Автосоздание trial-подписки — без неё ensure_subscription_active/
    # ensure_can_create_vehicle (app/services/subscription_service.py)
    # блокировали бы создание первой же машины у только что
    # зарегистрированной организации.
    subscription = Subscription(
        organization_id=organization.id,
        plan=SubscriptionPlan.starter,
        status=SubscriptionStatus.trial,
        vehicles_limit=DEFAULT_TRIAL_VEHICLES_LIMIT,
        price=0,
        next_billing_date=None,
    )
    db.add(subscription)

    user = User(
        organization_id=organization.id,
        phone=phone,
        name=user_name,
        role=UserRole.owner,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

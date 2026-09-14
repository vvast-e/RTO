"""Привязка организации к Telegram-чату по одноразовому коду.

Флоу: пользователь запрашивает код через
POST /api/organizations/me/telegram-link-code, отправляет боту команду
/start <код>; вебхук бота (POST /api/telegram/webhook) вызывает
consume_link_code — сопоставляет код с организацией и сохраняет chat_id
в Organization.telegram_chat_id.
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.models.telegram_link_code import TelegramLinkCode

CODE_TTL_MINUTES = 10


class TelegramLinkError(Exception):
    """Ошибка привязки чата с сообщением, пригодным для показа пользователю/лога."""


def _generate_code() -> str:
    return secrets.token_hex(4).upper()  # 8 hex-символов, например "A3F9C21B"


def create_link_code(db: Session, organization_id: uuid.UUID) -> TelegramLinkCode:
    """Создаёт новый одноразовый код привязки для организации."""
    now = datetime.now(timezone.utc)
    record = TelegramLinkCode(
        organization_id=organization_id,
        code=_generate_code(),
        expires_at=now + timedelta(minutes=CODE_TTL_MINUTES),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def consume_link_code(db: Session, code: str, chat_id: int) -> Organization:
    """Проверяет код и привязывает chat_id к организации.

    Бросает TelegramLinkError, если код не найден, уже использован или истёк.
    """
    now = datetime.now(timezone.utc)
    record = db.execute(
        select(TelegramLinkCode)
        .where(TelegramLinkCode.code == code.strip().upper())
        .order_by(TelegramLinkCode.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    if record is None or record.consumed_at is not None:
        raise TelegramLinkError("Код привязки не найден или уже использован")

    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if now > expires_at:
        raise TelegramLinkError("Срок действия кода истёк, запросите новый через приложение")

    record.consumed_at = now
    organization = db.get(Organization, record.organization_id)
    if organization is None:
        raise TelegramLinkError("Организация для этого кода не найдена")
    organization.telegram_chat_id = chat_id
    db.commit()
    db.refresh(organization)
    return organization

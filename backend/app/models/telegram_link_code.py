import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class TelegramLinkCode(UUIDPKMixin, TimestampMixin, Base):
    """Одноразовый код привязки организации к Telegram-чату.

    Пользователь получает код через POST /api/organizations/me/telegram-link-code
    и отправляет боту команду /start <код>; вебхук сопоставляет код с
    организацией и сохраняет chat_id в Organization.telegram_chat_id. Хранение
    в БД (а не in-memory/Redis) выбрано для простоты — коды короткоживущие
    (см. CODE_TTL_MINUTES в app/services/telegram_link.py) и низкочастотные,
    отдельная инфраструктура не оправдана, а таблица переживает перезапуск
    процесса, в отличие от in-memory словаря.
    """

    __tablename__ = "telegram_link_codes"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    code: Mapped[str] = mapped_column(String(16), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

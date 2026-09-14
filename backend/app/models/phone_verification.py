import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class VerificationPurpose(str, enum.Enum):
    register = "register"
    login = "login"


class PhoneVerificationCode(UUIDPKMixin, TimestampMixin, Base):
    """Одноразовый SMS-код для регистрации организации или входа пользователя."""

    __tablename__ = "phone_verification_codes"

    phone: Mapped[str] = mapped_column(String(20), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    purpose: Mapped[VerificationPurpose] = mapped_column(Enum(VerificationPurpose))
    # Заполняется только для сценария входа в уже существующую организацию;
    # при регистрации организация ещё не создана на момент отправки кода.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

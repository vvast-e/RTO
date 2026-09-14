import uuid
from datetime import date

from sqlalchemy import String, ForeignKey, BigInteger, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class Driver(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "drivers"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Номер карты водителя тахографа или табельный номер — используется для
    # сопоставления строк импорта из CSV/Excel-выгрузки тахографа с водителем.
    tachograph_card_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Срок действия водительского удостоверения — источник для автогенерации
    # напоминаний (app.services.reminder_generation). Nullable: не у всех
    # записей дата известна сразу, генерация просто пропускает записи с NULL.
    license_expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="drivers")

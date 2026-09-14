import uuid
import enum
from datetime import date

from sqlalchemy import String, ForeignKey, Enum, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class VehicleStatus(str, enum.Enum):
    active = "active"
    repair = "repair"
    inactive = "inactive"


class Vehicle(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    plate_number: Mapped[str] = mapped_column(String(20))
    brand_model: Mapped[str] = mapped_column(String(255))
    tachograph_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[VehicleStatus] = mapped_column(
        Enum(VehicleStatus), default=VehicleStatus.active
    )
    # Дата следующего планового техосмотра — источник для автогенерации
    # напоминаний (app.services.reminder_generation). Nullable: не у всех
    # записей дата известна сразу, генерация просто пропускает записи с NULL.
    next_inspection_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    organization: Mapped["Organization"] = relationship(back_populates="vehicles")

import uuid
import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Enum, DateTime, String, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class ViolationType(str, enum.Enum):
    # TODO: типы нарушений зависят от точных нормативов РТО (приказ Минтранса,
    # действующий с 01.09.2026). Значения ниже — рабочие заглушки под каркас
    # RtoCalculator, цифры лимитов НЕ зафиксированы и не должны использоваться
    # для реальных расчётов до сверки с официальным источником.
    daily_driving_exceeded = "daily_driving_exceeded"
    continuous_driving_exceeded = "continuous_driving_exceeded"
    daily_rest_insufficient = "daily_rest_insufficient"
    weekly_rest_insufficient = "weekly_rest_insufficient"
    biweekly_driving_exceeded = "biweekly_driving_exceeded"


class ViolationSeverity(str, enum.Enum):
    warning = "warning"
    violation = "violation"


class RtoViolation(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "rto_violations"

    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drivers.id"))
    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id"), nullable=True
    )
    violation_type: Mapped[ViolationType] = mapped_column(Enum(ViolationType))
    severity: Mapped[ViolationSeverity] = mapped_column(Enum(ViolationSeverity))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    driver: Mapped["Driver"] = relationship()

import uuid
import enum
from datetime import date

from sqlalchemy import ForeignKey, Enum, Date, Boolean, String, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class ReminderType(str, enum.Enum):
    rto_deadline = "rto_deadline"
    etrn_deadline = "etrn_deadline"
    vehicle_inspection = "vehicle_inspection"
    custom = "custom"


class Reminder(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "reminders"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    type: Mapped[ReminderType] = mapped_column(Enum(ReminderType))
    target_date: Mapped[date] = mapped_column(Date)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    organization: Mapped["Organization"] = relationship()

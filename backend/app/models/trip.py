import uuid
import enum
from datetime import datetime

from sqlalchemy import String, ForeignKey, Enum, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class TripStatus(str, enum.Enum):
    planned = "planned"
    in_progress = "in_progress"
    completed = "completed"


class Trip(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "trips"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("vehicles.id"))
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drivers.id"))
    start_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    start_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    end_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Numeric(10, 1), nullable=True)
    status: Mapped[TripStatus] = mapped_column(Enum(TripStatus), default=TripStatus.planned)

    vehicle: Mapped["Vehicle"] = relationship()
    driver: Mapped["Driver"] = relationship()

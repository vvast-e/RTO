import uuid
import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Enum, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class EntryType(str, enum.Enum):
    driving = "driving"
    rest = "rest"
    other_work = "other_work"
    availability = "availability"


class EntrySource(str, enum.Enum):
    manual = "manual"
    import_file = "import"


class WorkTimeEntry(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "work_time_entries"

    trip_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id"), nullable=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("drivers.id"))
    entry_type: Mapped[EntryType] = mapped_column(Enum(EntryType))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[EntrySource] = mapped_column(Enum(EntrySource), default=EntrySource.manual)

    driver: Mapped["Driver"] = relationship()

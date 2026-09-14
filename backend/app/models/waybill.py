import uuid
import enum
from datetime import date

from sqlalchemy import ForeignKey, Enum, Date, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class WaybillStatus(str, enum.Enum):
    draft = "draft"
    issued = "issued"


class Waybill(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "waybills"

    trip_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("trips.id"))
    document_number: Mapped[str] = mapped_column(String(50))
    issue_date: Mapped[date] = mapped_column(Date)
    pdf_file_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[WaybillStatus] = mapped_column(Enum(WaybillStatus), default=WaybillStatus.draft)

    trip: Mapped["Trip"] = relationship()

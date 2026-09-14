import uuid
from datetime import date, datetime

from pydantic import BaseModel


class DriverBase(BaseModel):
    full_name: str
    phone: str | None = None
    license_number: str | None = None
    tachograph_card_number: str | None = None
    license_expiry_date: date | None = None


class DriverCreate(DriverBase):
    pass


class DriverOut(DriverBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class DriverUpdate(BaseModel):
    """Только обновляемые поля — PATCH /api/drivers/{id} применяет их через
    exclude_unset, остальные поля записи не трогает."""

    full_name: str | None = None
    phone: str | None = None
    license_number: str | None = None
    tachograph_card_number: str | None = None
    license_expiry_date: date | None = None

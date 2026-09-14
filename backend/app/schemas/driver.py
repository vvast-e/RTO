import uuid

from pydantic import BaseModel


class DriverBase(BaseModel):
    full_name: str
    phone: str | None = None
    license_number: str | None = None
    tachograph_card_number: str | None = None


class DriverCreate(DriverBase):
    pass


class DriverOut(DriverBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

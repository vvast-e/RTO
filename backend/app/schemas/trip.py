import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.trip import TripStatus


class TripBase(BaseModel):
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    start_datetime: datetime
    end_datetime: datetime | None = None
    start_location: str | None = None
    end_location: str | None = None
    distance_km: float | None = None
    status: TripStatus = TripStatus.planned


class TripCreate(TripBase):
    pass


class TripOut(TripBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

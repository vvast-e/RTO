import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.waybill import WaybillStatus


class WaybillCreate(BaseModel):
    trip_id: uuid.UUID
    document_number: str
    issue_date: date


class WaybillOut(BaseModel):
    id: uuid.UUID
    trip_id: uuid.UUID
    document_number: str
    issue_date: date
    pdf_file_url: str | None
    status: WaybillStatus
    created_at: datetime

    class Config:
        from_attributes = True

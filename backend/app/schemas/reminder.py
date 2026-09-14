import uuid
from datetime import date, datetime

from pydantic import BaseModel

from app.models.reminder import ReminderType


class ReminderCreate(BaseModel):
    type: ReminderType
    target_date: date


class ReminderOut(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    type: ReminderType
    target_date: date
    sent: bool
    telegram_message_id: int | None
    created_at: datetime

    class Config:
        from_attributes = True

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.worktime import EntryType, EntrySource


class WorkTimeEntryBase(BaseModel):
    driver_id: uuid.UUID
    trip_id: uuid.UUID | None = None
    entry_type: EntryType
    start_time: datetime
    end_time: datetime | None = None
    source: EntrySource = EntrySource.manual


class WorkTimeEntryCreate(WorkTimeEntryBase):
    pass


class WorkTimeEntryOut(WorkTimeEntryBase):
    id: uuid.UUID

    class Config:
        from_attributes = True

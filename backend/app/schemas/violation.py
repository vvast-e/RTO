import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.violation import ViolationSeverity, ViolationType


class ViolationOut(BaseModel):
    id: uuid.UUID
    driver_id: uuid.UUID
    trip_id: uuid.UUID | None
    violation_type: ViolationType
    severity: ViolationSeverity
    detected_at: datetime
    description: str | None
    resolved: bool

    class Config:
        from_attributes = True

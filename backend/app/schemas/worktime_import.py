import uuid

from pydantic import BaseModel


class WorktimeImportRowError(BaseModel):
    row_number: int
    reason: str


class WorktimeImportReport(BaseModel):
    created: int
    skipped_duplicates: int
    failed: int
    errors: list[WorktimeImportRowError]
    created_entry_ids: list[uuid.UUID]

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.driver import Driver
from app.models.trip import Trip
from app.models.worktime import WorkTimeEntry
from app.schemas.worktime import WorkTimeEntryCreate, WorkTimeEntryOut

router = APIRouter(prefix="/api/worktime", tags=["worktime"])


def _get_owned_driver(driver_id: uuid.UUID, org_id: uuid.UUID, db: Session) -> Driver:
    driver = db.get(Driver, driver_id)
    if not driver or driver.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Водитель не найден")
    return driver


@router.get("", response_model=list[WorkTimeEntryOut])
def list_worktime_entries(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    driver_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
):
    stmt = (
        select(WorkTimeEntry)
        .join(Driver, WorkTimeEntry.driver_id == Driver.id)
        .where(Driver.organization_id == org_id)
    )
    if driver_id is not None:
        stmt = stmt.where(WorkTimeEntry.driver_id == driver_id)
    stmt = stmt.order_by(WorkTimeEntry.start_time).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=WorkTimeEntryOut, status_code=201)
def create_worktime_entry(
    payload: WorkTimeEntryCreate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    _get_owned_driver(payload.driver_id, org_id, db)
    if payload.trip_id is not None:
        trip = db.get(Trip, payload.trip_id)
        if not trip or trip.organization_id != org_id:
            raise HTTPException(status_code=404, detail="Рейс не найден")
    entry = WorkTimeEntry(**payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=WorkTimeEntryOut)
def get_worktime_entry(
    entry_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    entry = db.get(WorkTimeEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    _get_owned_driver(entry.driver_id, org_id, db)
    return entry

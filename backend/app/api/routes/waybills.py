import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.driver import Driver
from app.models.organization import Organization
from app.models.trip import Trip
from app.models.vehicle import Vehicle
from app.models.waybill import Waybill, WaybillStatus
from app.schemas.waybill import WaybillCreate, WaybillOut
from app.services.waybill_pdf import generate_waybill_pdf

router = APIRouter(prefix="/api/waybills", tags=["waybills"])


def _get_own_trip(db: Session, trip_id: uuid.UUID, org_id: uuid.UUID) -> Trip:
    """Waybill не хранит organization_id напрямую — принадлежность
    организации проверяется через связанный Trip, по аналогии с тем, как
    RtoViolation проверяется через Driver в /api/violations."""
    trip = db.get(Trip, trip_id)
    if trip is None or trip.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    return trip


def _get_own_waybill(db: Session, waybill_id: uuid.UUID, org_id: uuid.UUID) -> Waybill:
    waybill = db.get(Waybill, waybill_id)
    if waybill is None:
        raise HTTPException(status_code=404, detail="Путевой лист не найден")
    trip = db.get(Trip, waybill.trip_id)
    if trip is None or trip.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Путевой лист не найден")
    return waybill


@router.get("", response_model=list[WaybillOut])
def list_waybills(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    trip_id: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 50,
):
    stmt = (
        select(Waybill)
        .join(Trip, Waybill.trip_id == Trip.id)
        .where(Trip.organization_id == org_id)
    )
    if trip_id is not None:
        stmt = stmt.where(Waybill.trip_id == trip_id)
    stmt = stmt.order_by(Waybill.issue_date.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=WaybillOut, status_code=201)
def create_waybill(
    payload: WaybillCreate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    _get_own_trip(db, payload.trip_id, org_id)
    waybill = Waybill(**payload.model_dump())
    db.add(waybill)
    db.commit()
    db.refresh(waybill)
    return waybill


@router.get("/{waybill_id}", response_model=WaybillOut)
def get_waybill(
    waybill_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    return _get_own_waybill(db, waybill_id, org_id)


@router.post("/{waybill_id}/issue", response_model=WaybillOut)
def issue_waybill(
    waybill_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """Переводит путевой лист из draft в issued. Идемпотентно — повторный
    вызов для уже выданного листа не ошибка (по образцу resolve_violation)."""
    waybill = _get_own_waybill(db, waybill_id, org_id)
    if waybill.status != WaybillStatus.issued:
        waybill.status = WaybillStatus.issued
        db.commit()
        db.refresh(waybill)
    return waybill


@router.post("/{waybill_id}/generate", response_model=WaybillOut)
def generate_waybill(
    waybill_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    waybill = _get_own_waybill(db, waybill_id, org_id)
    trip = db.get(Trip, waybill.trip_id)
    driver = db.get(Driver, trip.driver_id)
    vehicle = db.get(Vehicle, trip.vehicle_id)
    organization = db.get(Organization, org_id)

    pdf_path = generate_waybill_pdf(waybill, trip, driver, vehicle, organization)
    waybill.pdf_file_url = pdf_path
    db.commit()
    db.refresh(waybill)
    return waybill

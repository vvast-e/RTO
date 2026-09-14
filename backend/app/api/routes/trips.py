import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.trip import Trip
from app.schemas.trip import TripCreate, TripOut

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.get("", response_model=list[TripOut])
def list_trips(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    stmt = select(Trip).where(Trip.organization_id == org_id).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=TripOut, status_code=201)
def create_trip(
    payload: TripCreate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    trip = Trip(organization_id=org_id, **payload.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("/{trip_id}", response_model=TripOut)
def get_trip(
    trip_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    trip = db.get(Trip, trip_id)
    if not trip or trip.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Рейс не найден")
    return trip

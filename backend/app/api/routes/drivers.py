import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.driver import Driver
from app.schemas.driver import DriverCreate, DriverOut, DriverUpdate

router = APIRouter(prefix="/api/drivers", tags=["drivers"])


@router.get("", response_model=list[DriverOut])
def list_drivers(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    stmt = select(Driver).where(Driver.organization_id == org_id).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=DriverOut, status_code=201)
def create_driver(
    payload: DriverCreate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    driver = Driver(organization_id=org_id, **payload.model_dump())
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(
    driver_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    driver = db.get(Driver, driver_id)
    if not driver or driver.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Водитель не найден")
    return driver


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(
    driver_id: uuid.UUID,
    payload: DriverUpdate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    driver = db.get(Driver, driver_id)
    if not driver or driver.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Водитель не найден")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(driver, field, value)
    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/{driver_id}", status_code=204)
def delete_driver(
    driver_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    driver = db.get(Driver, driver_id)
    if not driver or driver.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Водитель не найден")
    db.delete(driver)
    db.commit()

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.driver import Driver
from app.models.violation import RtoViolation, ViolationSeverity
from app.schemas.violation import ViolationOut

router = APIRouter(prefix="/api/violations", tags=["violations"])


@router.get("", response_model=list[ViolationOut])
def list_violations(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
    driver_id: uuid.UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    severity: ViolationSeverity | None = None,
    resolved: bool | None = None,
    skip: int = 0,
    limit: int = 50,
):
    stmt = (
        select(RtoViolation)
        .join(Driver, RtoViolation.driver_id == Driver.id)
        .where(Driver.organization_id == org_id)
    )
    if driver_id is not None:
        stmt = stmt.where(RtoViolation.driver_id == driver_id)
    if date_from is not None:
        stmt = stmt.where(RtoViolation.detected_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(RtoViolation.detected_at <= date_to)
    if severity is not None:
        stmt = stmt.where(RtoViolation.severity == severity)
    if resolved is not None:
        stmt = stmt.where(RtoViolation.resolved == resolved)
    stmt = stmt.order_by(RtoViolation.detected_at.desc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


@router.post("/{violation_id}/resolve", response_model=ViolationOut)
def resolve_violation(
    violation_id: uuid.UUID,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    """Помечает нарушение закрытым. Идемпотентно: повторный вызов для уже
    закрытого нарушения не является ошибкой и просто возвращает его текущее
    состояние."""
    violation = db.get(RtoViolation, violation_id)
    if violation is None:
        raise HTTPException(status_code=404, detail="Нарушение не найдено")
    driver = db.get(Driver, violation.driver_id)
    if driver is None or driver.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Нарушение не найдено")

    if not violation.resolved:
        violation.resolved = True
        db.commit()
        db.refresh(violation)
    return violation

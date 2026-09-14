"""Celery-таски пересчёта РТО. Тонкие обёртки над app.services.rto_pipeline —
вся логика (и её идемпотентность) покрыта тестами на самой функции без брокера."""

import uuid
from datetime import datetime

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.driver import Driver
from app.services.rto_pipeline import recalculate_rto_for_driver


@celery_app.task(name="rto.recalculate_for_driver")
def recalculate_rto_for_driver_task(driver_id: str, period_start: str, period_end: str) -> int:
    """Пересчитывает нарушения РТО одного водителя за период. Возвращает
    количество вновь созданных записей RtoViolation."""
    db = SessionLocal()
    try:
        created = recalculate_rto_for_driver(
            db,
            uuid.UUID(driver_id),
            datetime.fromisoformat(period_start),
            datetime.fromisoformat(period_end),
        )
        return len(created)
    finally:
        db.close()


@celery_app.task(name="rto.recalculate_for_organization")
def recalculate_rto_for_organization_task(
    organization_id: str, period_start: str, period_end: str
) -> int:
    """Пересчитывает нарушения РТО для всех водителей организации за период."""
    db = SessionLocal()
    try:
        driver_ids = (
            db.execute(select(Driver.id).where(Driver.organization_id == uuid.UUID(organization_id)))
            .scalars()
            .all()
        )
        start = datetime.fromisoformat(period_start)
        end = datetime.fromisoformat(period_end)
        total = 0
        for driver_id in driver_ids:
            total += len(recalculate_rto_for_driver(db, driver_id, start, end))
        return total
    finally:
        db.close()

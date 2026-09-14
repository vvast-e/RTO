"""Celery-таски пересчёта РТО. Тонкие обёртки над app.services.rto_pipeline —
вся логика (и её идемпотентность) покрыта тестами на самой функции без брокера."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.driver import Driver
from app.models.organization import Organization
from app.services.rto_pipeline import recalculate_rto_for_driver

# Скользящее окно периодического пересчёта: беспокоиться только о свежих
# записях, а не пересчитывать всю историю каждый раз. 2 суток с запасом
# перекрывают проверку ежедневного отдыха на границе календарных дней
# (см. RtoCalculator._check_daily_rest) даже если предыдущий запуск
# по какой-то причине пропущен.
PERIODIC_RECALC_WINDOW = timedelta(days=2)


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


@celery_app.task(name="rto.recalculate_for_all_organizations")
def recalculate_rto_for_all_organizations_task() -> int:
    """Периодический таск (celery beat): ставит в очередь пересчёт РТО для
    каждой организации в БД за скользящее окно PERIODIC_RECALC_WINDOW до
    текущего момента. Не пересчитывает всю историю — только свежие записи.

    Возвращает количество организаций, для которых был поставлен пересчёт.
    """
    db = SessionLocal()
    try:
        organization_ids = db.execute(select(Organization.id)).scalars().all()
    finally:
        db.close()

    period_end = datetime.utcnow()
    period_start = period_end - PERIODIC_RECALC_WINDOW
    for organization_id in organization_ids:
        recalculate_rto_for_organization_task.delay(
            str(organization_id), period_start.isoformat(), period_end.isoformat()
        )
    return len(organization_ids)

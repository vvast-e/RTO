"""Синхронный вызов Celery-таска пересчёта РТО (без брокера — Celery это
поддерживает через прямой вызов .run()/обёрнутой функции)."""

from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from app.db.session import SessionLocal
from app.models.driver import Driver
from app.models.organization import Organization
from app.models.violation import RtoViolation
from app.models.worktime import EntryType, WorkTimeEntry
from app.tasks.rto_tasks import (
    recalculate_rto_for_driver_task,
    recalculate_rto_for_organization_task,
)

BASE_DAY = datetime(2026, 9, 14, 6, 0)


def test_recalculate_rto_for_driver_task_uses_sessionlocal(db_engine, monkeypatch):
    session_local = sessionmaker(bind=db_engine)
    monkeypatch.setattr("app.tasks.rto_tasks.SessionLocal", session_local)

    db = session_local()
    try:
        org = Organization(name="Тестовая организация")
        db.add(org)
        db.flush()
        driver = Driver(organization_id=org.id, full_name="Иван Петров")
        db.add(driver)
        db.flush()
        db.add(
            WorkTimeEntry(
                driver_id=driver.id,
                entry_type=EntryType.driving,
                start_time=BASE_DAY,
                end_time=BASE_DAY + timedelta(hours=5),
            )
        )
        db.add(
            WorkTimeEntry(
                driver_id=driver.id,
                entry_type=EntryType.rest,
                start_time=BASE_DAY + timedelta(hours=5),
                end_time=BASE_DAY + timedelta(hours=17),
            )
        )
        db.commit()
        driver_id = str(driver.id)
    finally:
        db.close()

    period_start = (BASE_DAY - timedelta(days=1)).isoformat()
    period_end = (BASE_DAY + timedelta(days=1)).isoformat()

    created_count = recalculate_rto_for_driver_task.run(driver_id, period_start, period_end)
    assert created_count == 1

    # повторный запуск идемпотентен
    created_count_again = recalculate_rto_for_driver_task.run(driver_id, period_start, period_end)
    assert created_count_again == 0

    db = session_local()
    try:
        assert db.query(RtoViolation).count() == 1
    finally:
        db.close()


def test_recalculate_rto_for_organization_task_covers_all_drivers(db_engine, monkeypatch):
    session_local = sessionmaker(bind=db_engine)
    monkeypatch.setattr("app.tasks.rto_tasks.SessionLocal", session_local)

    db = session_local()
    try:
        org = Organization(name="Тестовая организация")
        db.add(org)
        db.flush()
        drivers = [
            Driver(organization_id=org.id, full_name="Водитель Один"),
            Driver(organization_id=org.id, full_name="Водитель Два"),
        ]
        db.add_all(drivers)
        db.flush()
        for driver in drivers:
            db.add(
                WorkTimeEntry(
                    driver_id=driver.id,
                    entry_type=EntryType.driving,
                    start_time=BASE_DAY,
                    end_time=BASE_DAY + timedelta(hours=5),
                )
            )
            db.add(
                WorkTimeEntry(
                    driver_id=driver.id,
                    entry_type=EntryType.rest,
                    start_time=BASE_DAY + timedelta(hours=5),
                    end_time=BASE_DAY + timedelta(hours=17),
                )
            )
        db.commit()
        org_id = str(org.id)
    finally:
        db.close()

    period_start = (BASE_DAY - timedelta(days=1)).isoformat()
    period_end = (BASE_DAY + timedelta(days=1)).isoformat()

    total_created = recalculate_rto_for_organization_task.run(org_id, period_start, period_end)
    assert total_created == 2

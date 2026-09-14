"""Тесты app.services.rto_pipeline.recalculate_rto_for_driver — связки
RtoCalculator с БД (без Celery-брокера, синхронный вызов функции)."""

from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from app.models.driver import Driver
from app.models.organization import Organization
from app.models.violation import RtoViolation
from app.models.worktime import EntryType, WorkTimeEntry
from app.services.rto_pipeline import recalculate_rto_for_driver

BASE_DAY = datetime(2026, 9, 14, 6, 0)


def _make_driver(db):
    org = Organization(name="Тестовая организация")
    db.add(org)
    db.flush()
    driver = Driver(organization_id=org.id, full_name="Иван Петров")
    db.add(driver)
    db.commit()
    return driver


def _add_entry(db, driver, entry_type, start, hours):
    entry = WorkTimeEntry(
        driver_id=driver.id,
        entry_type=entry_type,
        start_time=start,
        end_time=start + timedelta(hours=hours),
    )
    db.add(entry)
    db.commit()
    return entry


def test_recalculate_creates_violations_from_worktime_entries(db_engine):
    session_local = sessionmaker(bind=db_engine)
    db = session_local()
    try:
        driver = _make_driver(db)
        # непрерывное вождение 5ч без перерыва > лимита 4.5ч
        _add_entry(db, driver, EntryType.driving, BASE_DAY, 5.0)
        _add_entry(db, driver, EntryType.rest, BASE_DAY + timedelta(hours=5), 12.0)

        created = recalculate_rto_for_driver(
            db, driver.id, BASE_DAY - timedelta(days=1), BASE_DAY + timedelta(days=1)
        )
        assert len(created) == 1

        stored = db.query(RtoViolation).filter(RtoViolation.driver_id == driver.id).all()
        assert len(stored) == 1
    finally:
        db.close()


def test_recalculate_is_idempotent_on_rerun(db_engine):
    session_local = sessionmaker(bind=db_engine)
    db = session_local()
    try:
        driver = _make_driver(db)
        _add_entry(db, driver, EntryType.driving, BASE_DAY, 5.0)
        _add_entry(db, driver, EntryType.rest, BASE_DAY + timedelta(hours=5), 12.0)

        period_start = BASE_DAY - timedelta(days=1)
        period_end = BASE_DAY + timedelta(days=1)

        first_run = recalculate_rto_for_driver(db, driver.id, period_start, period_end)
        second_run = recalculate_rto_for_driver(db, driver.id, period_start, period_end)

        assert len(first_run) == 1
        assert len(second_run) == 0  # повторный запуск не создаёт дублей

        stored = db.query(RtoViolation).filter(RtoViolation.driver_id == driver.id).all()
        assert len(stored) == 1
    finally:
        db.close()


def test_recalculate_no_violations_for_normal_entries(db_engine):
    session_local = sessionmaker(bind=db_engine)
    db = session_local()
    try:
        driver = _make_driver(db)
        _add_entry(db, driver, EntryType.driving, BASE_DAY, 4.0)
        _add_entry(db, driver, EntryType.rest, BASE_DAY + timedelta(hours=4), 12.0)

        created = recalculate_rto_for_driver(
            db, driver.id, BASE_DAY - timedelta(days=1), BASE_DAY + timedelta(days=1)
        )
        assert created == []
    finally:
        db.close()

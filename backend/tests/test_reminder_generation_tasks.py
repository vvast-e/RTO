"""Синхронный вызов Celery-таска автогенерации напоминаний (без брокера —
через прямой вызов .run(), как и в test_rto_tasks.py/test_reminder_tasks.py)."""

from datetime import date, timedelta

from sqlalchemy.orm import sessionmaker

from app.models.driver import Driver
from app.models.organization import Organization
from app.models.reminder import Reminder
from app.models.vehicle import Vehicle
from app.tasks.reminder_generation_tasks import generate_reminders_for_all_organizations_task

TODAY = date(2026, 9, 15)


def _make_org(db, name: str) -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.flush()
    return org


def test_generates_for_every_organization_in_isolation(db_engine, monkeypatch):
    session_local = sessionmaker(bind=db_engine)
    monkeypatch.setattr("app.tasks.reminder_generation_tasks.SessionLocal", session_local)
    monkeypatch.setattr(
        "app.services.reminder_generation.date",
        type("_FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}),
    )

    db = session_local()
    try:
        org_a = _make_org(db, "Альфа")
        org_b = _make_org(db, "Бета")
        db.add(
            Vehicle(
                organization_id=org_a.id,
                plate_number="А000АА00",
                brand_model="КамАЗ",
                next_inspection_date=TODAY + timedelta(days=5),
            )
        )
        db.add(
            Driver(
                organization_id=org_b.id,
                full_name="Водитель Бета",
                license_expiry_date=TODAY + timedelta(days=7),
            )
        )
        db.commit()
    finally:
        db.close()

    total_created = generate_reminders_for_all_organizations_task.run()
    assert total_created == 2

    db = session_local()
    try:
        reminders = db.query(Reminder).all()
        assert len(reminders) == 2
        org_ids = {r.organization_id for r in reminders}
        assert len(org_ids) == 2
    finally:
        db.close()


def test_is_idempotent_across_repeated_runs(db_engine, monkeypatch):
    session_local = sessionmaker(bind=db_engine)
    monkeypatch.setattr("app.tasks.reminder_generation_tasks.SessionLocal", session_local)
    monkeypatch.setattr(
        "app.services.reminder_generation.date",
        type("_FixedDate", (date,), {"today": classmethod(lambda cls: TODAY)}),
    )

    db = session_local()
    try:
        org = _make_org(db, "Организация")
        db.add(
            Vehicle(
                organization_id=org.id,
                plate_number="В111ВВ11",
                brand_model="Газель",
                next_inspection_date=TODAY + timedelta(days=3),
            )
        )
        db.commit()
    finally:
        db.close()

    first_run = generate_reminders_for_all_organizations_task.run()
    second_run = generate_reminders_for_all_organizations_task.run()
    assert first_run == 1
    assert second_run == 0

    db = session_local()
    try:
        assert db.query(Reminder).count() == 1
    finally:
        db.close()

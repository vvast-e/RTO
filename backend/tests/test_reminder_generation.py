"""Юнит-тесты app.services.reminder_generation: генерация напоминаний из
Vehicle.next_inspection_date / Driver.license_expiry_date, идемпотентность,
окно генерации, изоляция по организациям."""

from datetime import date, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.driver import Driver
from app.models.organization import Organization
from app.models.reminder import Reminder, ReminderType
from app.models.vehicle import Vehicle
from app.services.reminder_generation import (
    GENERATION_WINDOW_DAYS,
    generate_reminders_for_organization,
)

TODAY = date(2026, 9, 15)


@pytest.fixture()
def session_local(db_engine):
    return sessionmaker(bind=db_engine)


def _make_org(db, name: str = "Организация") -> Organization:
    org = Organization(name=name)
    db.add(org)
    db.flush()
    return org


def test_generates_reminder_for_vehicle_inspection_within_window(session_local):
    db = session_local()
    try:
        org = _make_org(db)
        vehicle = Vehicle(
            organization_id=org.id,
            plate_number="А000АА00",
            brand_model="КамАЗ",
            next_inspection_date=TODAY + timedelta(days=5),
        )
        db.add(vehicle)
        db.commit()
        org_id, vehicle_id = org.id, vehicle.id

        created = generate_reminders_for_organization(db, org_id, today=TODAY)
        assert created == 1

        reminders = db.query(Reminder).all()
        assert len(reminders) == 1
        assert reminders[0].type == ReminderType.vehicle_inspection
        assert reminders[0].target_date == TODAY + timedelta(days=5)
        assert reminders[0].vehicle_id == vehicle_id
    finally:
        db.close()


def test_generates_reminder_for_driver_license_expiry_within_window(session_local):
    db = session_local()
    try:
        org = _make_org(db)
        driver = Driver(
            organization_id=org.id,
            full_name="Иван Петров",
            license_expiry_date=TODAY + timedelta(days=10),
        )
        db.add(driver)
        db.commit()
        org_id, driver_id = org.id, driver.id

        created = generate_reminders_for_organization(db, org_id, today=TODAY)
        assert created == 1

        reminders = db.query(Reminder).all()
        assert len(reminders) == 1
        assert reminders[0].type == ReminderType.driver_license_expiry
        assert reminders[0].target_date == TODAY + timedelta(days=10)
        assert reminders[0].driver_id == driver_id
    finally:
        db.close()


def test_no_reminder_for_dates_without_value(session_local):
    db = session_local()
    try:
        org = _make_org(db)
        db.add(Vehicle(organization_id=org.id, plate_number="В111ВВ11", brand_model="Газель"))
        db.add(Driver(organization_id=org.id, full_name="Без даты"))
        db.commit()
        org_id = org.id

        created = generate_reminders_for_organization(db, org_id, today=TODAY)
        assert created == 0
        assert db.query(Reminder).count() == 0
    finally:
        db.close()


def test_no_reminder_for_dates_outside_window(session_local):
    db = session_local()
    try:
        org = _make_org(db)
        too_far = TODAY + timedelta(days=GENERATION_WINDOW_DAYS + 1)
        in_past = TODAY - timedelta(days=1)
        db.add(
            Vehicle(
                organization_id=org.id,
                plate_number="С222СС22",
                brand_model="ЗИЛ",
                next_inspection_date=too_far,
            )
        )
        db.add(
            Driver(
                organization_id=org.id,
                full_name="Просроченные права",
                license_expiry_date=in_past,
            )
        )
        db.commit()
        org_id = org.id

        created = generate_reminders_for_organization(db, org_id, today=TODAY)
        assert created == 0
        assert db.query(Reminder).count() == 0
    finally:
        db.close()


def test_is_idempotent_across_repeated_runs(session_local):
    db = session_local()
    try:
        org = _make_org(db)
        db.add(
            Vehicle(
                organization_id=org.id,
                plate_number="Е333ЕЕ33",
                brand_model="МАЗ",
                next_inspection_date=TODAY + timedelta(days=3),
            )
        )
        db.commit()
        org_id = org.id

        first_run = generate_reminders_for_organization(db, org_id, today=TODAY)
        second_run = generate_reminders_for_organization(db, org_id, today=TODAY)
        assert first_run == 1
        assert second_run == 0
        assert db.query(Reminder).count() == 1
    finally:
        db.close()


def test_two_vehicles_with_same_deadline_both_get_reminders(session_local):
    """Регрессия на схлопывание по organization_id+type+target_date без
    привязки к vehicle_id — см. docstring reminder_generation.py."""
    db = session_local()
    try:
        org = _make_org(db)
        same_date = TODAY + timedelta(days=2)
        v1 = Vehicle(
            organization_id=org.id,
            plate_number="К444КК44",
            brand_model="Volvo",
            next_inspection_date=same_date,
        )
        v2 = Vehicle(
            organization_id=org.id,
            plate_number="М555ММ55",
            brand_model="Scania",
            next_inspection_date=same_date,
        )
        db.add_all([v1, v2])
        db.commit()
        org_id = org.id

        created = generate_reminders_for_organization(db, org_id, today=TODAY)
        assert created == 2
        assert db.query(Reminder).count() == 2
    finally:
        db.close()


def test_organizations_are_isolated(session_local):
    db = session_local()
    try:
        org_a = _make_org(db, "Альфа")
        org_b = _make_org(db, "Бета")
        db.add(
            Vehicle(
                organization_id=org_a.id,
                plate_number="Н666НН66",
                brand_model="ГАЗ",
                next_inspection_date=TODAY + timedelta(days=1),
            )
        )
        db.add(
            Vehicle(
                organization_id=org_b.id,
                plate_number="Р777РР77",
                brand_model="УАЗ",
                next_inspection_date=TODAY + timedelta(days=1),
            )
        )
        db.commit()
        org_a_id = org_a.id

        created = generate_reminders_for_organization(db, org_a_id, today=TODAY)
        assert created == 1
        reminders = db.query(Reminder).all()
        assert len(reminders) == 1
        assert reminders[0].organization_id == org_a_id
    finally:
        db.close()

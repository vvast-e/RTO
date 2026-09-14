"""Автогенерация напоминаний из сроков ТО (Vehicle.next_inspection_date) и
истечения водительских удостоверений (Driver.license_expiry_date).
Периодический запуск — Celery beat, см. app.tasks.reminder_generation_tasks.

Идемпотентность: перед созданием напоминания проверяется, нет ли уже
несотправленного Reminder с тем же organization_id + type + target_date +
vehicle_id/driver_id. Привязка к конкретной записи-источнику
(Reminder.vehicle_id / Reminder.driver_id) нужна потому, что одного
organization_id + type + target_date недостаточно — два разных автомобиля
(или водителя) с совпадающим дедлайном иначе дали бы коллизию и напоминание
создалось бы только для одного из них.
"""

import uuid
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.reminder import Reminder, ReminderType
from app.models.vehicle import Vehicle

# За сколько дней до дедлайна создавать напоминание. 14 дней — разумный
# дефолт для MVP: достаточно времени на запись на ТО / продление прав, но
# не создаёт напоминания сильно заранее.
GENERATION_WINDOW_DAYS = 14


def _reminder_already_exists(
    db: Session,
    organization_id: uuid.UUID,
    reminder_type: ReminderType,
    target_date: date,
    *,
    vehicle_id: uuid.UUID | None = None,
    driver_id: uuid.UUID | None = None,
) -> bool:
    stmt = (
        select(Reminder.id)
        .where(Reminder.organization_id == organization_id)
        .where(Reminder.type == reminder_type)
        .where(Reminder.target_date == target_date)
        .where(Reminder.sent.is_(False))
    )
    if vehicle_id is not None:
        stmt = stmt.where(Reminder.vehicle_id == vehicle_id)
    if driver_id is not None:
        stmt = stmt.where(Reminder.driver_id == driver_id)
    return db.execute(stmt).first() is not None


def generate_reminders_for_organization(
    db: Session, organization_id: uuid.UUID, today: date | None = None
) -> int:
    """Находит Vehicle/Driver организации с дедлайном в пределах ближайших
    GENERATION_WINDOW_DAYS дней и создаёт для них напоминания. Записи с
    NULL-датой пропускаются. Возвращает количество вновь созданных
    напоминаний."""
    today = today or date.today()
    horizon = today + timedelta(days=GENERATION_WINDOW_DAYS)
    created = 0

    vehicles = (
        db.execute(
            select(Vehicle)
            .where(Vehicle.organization_id == organization_id)
            .where(Vehicle.next_inspection_date.is_not(None))
            .where(Vehicle.next_inspection_date >= today)
            .where(Vehicle.next_inspection_date <= horizon)
        )
        .scalars()
        .all()
    )
    for vehicle in vehicles:
        if _reminder_already_exists(
            db,
            organization_id,
            ReminderType.vehicle_inspection,
            vehicle.next_inspection_date,
            vehicle_id=vehicle.id,
        ):
            continue
        db.add(
            Reminder(
                organization_id=organization_id,
                type=ReminderType.vehicle_inspection,
                target_date=vehicle.next_inspection_date,
                vehicle_id=vehicle.id,
            )
        )
        created += 1

    drivers = (
        db.execute(
            select(Driver)
            .where(Driver.organization_id == organization_id)
            .where(Driver.license_expiry_date.is_not(None))
            .where(Driver.license_expiry_date >= today)
            .where(Driver.license_expiry_date <= horizon)
        )
        .scalars()
        .all()
    )
    for driver in drivers:
        if _reminder_already_exists(
            db,
            organization_id,
            ReminderType.driver_license_expiry,
            driver.license_expiry_date,
            driver_id=driver.id,
        ):
            continue
        db.add(
            Reminder(
                organization_id=organization_id,
                type=ReminderType.driver_license_expiry,
                target_date=driver.license_expiry_date,
                driver_id=driver.id,
            )
        )
        created += 1

    db.commit()
    return created

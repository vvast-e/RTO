"""Celery-таск автогенерации напоминаний из сроков ТО и истечения
водительских удостоверений. Тонкая обёртка над
app.services.reminder_generation — по образцу
rto_tasks.recalculate_rto_for_all_organizations_task: проходит по всем
Organization в БД и для каждой вызывает сервис генерации."""

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.services.reminder_generation import generate_reminders_for_organization


@celery_app.task(name="reminders.generate_for_all_organizations")
def generate_reminders_for_all_organizations_task() -> int:
    """Периодический таск (celery beat): для каждой организации в БД
    генерирует напоминания о приближающихся сроках ТО/прав (см.
    generate_reminders_for_organization). Возвращает суммарное количество
    вновь созданных напоминаний по всем организациям."""
    db = SessionLocal()
    try:
        organization_ids = db.execute(select(Organization.id)).scalars().all()
        total = 0
        for organization_id in organization_ids:
            total += generate_reminders_for_organization(db, organization_id)
        return total
    finally:
        db.close()

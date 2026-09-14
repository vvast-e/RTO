from celery import Celery

from app.core.config import settings

celery_app = Celery("rto", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.beat_schedule = {
    # MVP: организаций мало, раз в час достаточно и не создаёт лишней
    # нагрузки — сам пересчёт по каждой организации идёт за скользящее
    # окно (см. PERIODIC_RECALC_WINDOW в app.tasks.rto_tasks), а не за
    # всю историю.
    "recalculate-rto-for-all-organizations-hourly": {
        "task": "rto.recalculate_for_all_organizations",
        "schedule": 3600.0,
    },
    # Напоминания хранят только дату (target_date), не время — просрочка
    # определяется по календарному дню, а не по минутам, поэтому частая
    # проверка ничего не выигрывает. Раз в час — тот же интервал, что и у
    # пересчёта РТО выше, этого достаточно, чтобы напоминание ушло в течение
    # часа после наступления его даты.
    "send-due-reminders-hourly": {
        "task": "reminders.send_due",
        "schedule": 3600.0,
    },
    # Даты ТО/прав (Vehicle.next_inspection_date, Driver.license_expiry_date)
    # меняются редко и генерация смотрит на окно в GENERATION_WINDOW_DAYS
    # (14 дней) вперёд — в отличие от пересчёта РТО и рассылки напоминаний
    # выше, здесь часовая частота ничего не выигрывает и только дублирует
    # нагрузку. Раз в сутки достаточно, чтобы новое напоминание появилось не
    # позднее чем через день после того, как дедлайн попал в окно генерации.
    "generate-reminders-daily": {
        "task": "reminders.generate_for_all_organizations",
        "schedule": 86400.0,
    },
}

# Регистрирует таски пересчёта РТО и рассылки/генерации напоминаний в
# celery_app (импорт в конце файла, чтобы избежать циклического импорта
# celery_app <-> app.tasks.*).
from app.tasks import reminder_generation_tasks  # noqa: E402,F401
from app.tasks import reminder_tasks  # noqa: E402,F401
from app.tasks import rto_tasks  # noqa: E402,F401

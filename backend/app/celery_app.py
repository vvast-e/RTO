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
}

# Регистрирует таски пересчёта РТО в celery_app (импорт в конце файла,
# чтобы избежать циклического импорта celery_app <-> app.tasks.rto_tasks).
from app.tasks import rto_tasks  # noqa: E402,F401

from celery import Celery

from app.core.config import settings

celery_app = Celery("rto", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.beat_schedule = {
    # TODO: подключить периодический пересчёт РТО (rto.recalculate_for_organization)
    # для всех организаций, когда появится список организаций/расписание в БД.
}

# Регистрирует таски пересчёта РТО в celery_app (импорт в конце файла,
# чтобы избежать циклического импорта celery_app <-> app.tasks.rto_tasks).
from app.tasks import rto_tasks  # noqa: E402,F401

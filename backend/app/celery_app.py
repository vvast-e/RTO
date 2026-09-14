from celery import Celery

from app.core.config import settings

celery_app = Celery("rto", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.beat_schedule = {
    # TODO: подключить реальную задачу пересчёта РТО после реализации
    # Celery-таска recalculate_rto_for_all_drivers.
}

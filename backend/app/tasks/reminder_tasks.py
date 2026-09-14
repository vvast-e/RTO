"""Celery-таск автоматической рассылки просроченных напоминаний. По аналогии
с app.tasks.rto_tasks — тонкая обёртка над app.services.reminder_service,
периодический запуск через celery beat (см. beat_schedule в app.celery_app)."""

import logging
from datetime import date

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.reminder import Reminder
from app.services.reminder_sender import TelegramChatNotLinkedError, get_reminder_sender
from app.services.reminder_service import send_reminder

logger = logging.getLogger("app.reminders")


@celery_app.task(name="reminders.send_due")
def send_due_reminders_task() -> int:
    """Находит неотправленные напоминания с истёкшим сроком (target_date <=
    сегодня) и отправляет их через настроенный ReminderSender.

    Организации без привязанного Telegram-чата не роняют весь таск —
    TelegramChatNotLinkedError логируется, напоминание остаётся
    неотправленным и будет подхвачено на следующем запуске (как только чат
    привяжут). Возвращает количество успешно отправленных напоминаний.
    """
    db = SessionLocal()
    sent_count = 0
    try:
        sender = get_reminder_sender()
        due_reminders = (
            db.execute(
                select(Reminder)
                .where(Reminder.sent.is_(False))
                .where(Reminder.target_date <= date.today())
            )
            .scalars()
            .all()
        )
        for reminder in due_reminders:
            try:
                send_reminder(db, reminder, sender)
                sent_count += 1
            except TelegramChatNotLinkedError:
                logger.info(
                    "[Reminder auto-send] Организация %s: чат не привязан, напоминание %s пропущено",
                    reminder.organization_id,
                    reminder.id,
                )
        return sent_count
    finally:
        db.close()

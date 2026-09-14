"""Общая логика отправки одного напоминания — переиспользуется ручным
эндпоинтом POST /api/reminders/{id}/send (app/api/routes/reminders.py) и
периодическим Celery-таском автоматической рассылки (app/tasks/reminder_tasks.py),
чтобы не дублировать проставление sent/telegram_message_id и работу с
sender'ом в двух местах.
"""

from sqlalchemy.orm import Session

from app.models.reminder import Reminder
from app.services.reminder_sender import ReminderSender


def send_reminder(db: Session, reminder: Reminder, sender: ReminderSender) -> Reminder:
    """Отправляет напоминание через переданный sender и помечает его отправленным.

    Коммитит изменения сам. Исключения sender'а (например,
    TelegramChatNotLinkedError) не перехватываются — их обрабатывает вызывающий
    код по своим правилам (409 в API, лог+пропуск в периодическом таске).
    """
    telegram_message_id = sender.send(reminder)
    reminder.sent = True
    reminder.telegram_message_id = telegram_message_id
    db.commit()
    db.refresh(reminder)
    return reminder

"""
Абстракция над отправкой напоминаний.

На этом этапе реальной интеграции с Telegram-ботом ещё нет (см. TODO в
README/памяти проекта) — единственная реализация ConsoleReminderSender
только логирует напоминание, как ConsoleSmsSender в app/services/sms.py.
Когда бот появится, TelegramReminderSender подключается заменой одной
реализации в get_reminder_sender(), без изменений в CRUD/API.
"""

import logging
from abc import ABC, abstractmethod

from app.models.reminder import Reminder

logger = logging.getLogger("app.reminders")


class ReminderSender(ABC):
    @abstractmethod
    def send(self, reminder: Reminder) -> int | None:
        """Отправить уведомление по напоминанию.

        Возвращает telegram_message_id отправленного сообщения, либо None,
        если у реализации нет такого идентификатора (как у консольной
        заглушки).
        """


class ConsoleReminderSender(ReminderSender):
    """Заглушка для разработки и тестов — напоминание попадает только в лог."""

    def send(self, reminder: Reminder) -> int | None:
        logger.info(
            "[Reminder mock] Организация %s: %s на %s",
            reminder.organization_id,
            reminder.type.value,
            reminder.target_date,
        )
        return None


def get_reminder_sender() -> ReminderSender:
    # TODO: при подключении Telegram-бота — выбор реализации по конфигу,
    # аналогично get_sms_sender() в app/services/sms.py.
    return ConsoleReminderSender()

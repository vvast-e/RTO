"""Абстракция над отправкой напоминаний.

ConsoleReminderSender — заглушка для разработки и тестов (лог вместо
реальной отправки). TelegramReminderSender отправляет сообщение через
HTTP Bot API Telegram напрямую через httpx (без python-telegram-bot —
нужен только один метод sendMessage, тащить SDK ради этого избыточно;
тот же подход, что и у SmsRuSender в app/services/sms.py). Выбор
реализации — get_reminder_sender() по конфигу TELEGRAM_PROVIDER
(console/telegram), по аналогии с SMS_PROVIDER.
"""

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings
from app.models.reminder import Reminder, ReminderType

logger = logging.getLogger("app.reminders")

_TYPE_LABELS = {
    ReminderType.rto_deadline: "Истекает срок соблюдения режима труда и отдыха (РТО)",
    ReminderType.etrn_deadline: "Истекает срок электронной транспортной накладной (ЭТрН)",
    ReminderType.vehicle_inspection: "Требуется техосмотр автомобиля",
    ReminderType.custom: "Напоминание",
}


class ReminderSender(ABC):
    @abstractmethod
    def send(self, reminder: Reminder) -> int | None:
        """Отправить уведомление по напоминанию.

        Возвращает telegram_message_id отправленного сообщения, либо None,
        если у реализации нет такого идентификатора (как у консольной
        заглушки).
        """


class TelegramChatNotLinkedError(Exception):
    """У организации нет привязанного Telegram-чата — отправка невозможна."""


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


class TelegramReminderSender(ReminderSender):
    """Отправка через HTTP Bot API Telegram (https://core.telegram.org/bots/api)."""

    def __init__(self, bot_token: str):
        self.api_base = f"https://api.telegram.org/bot{bot_token}"

    def send(self, reminder: Reminder) -> int | None:
        chat_id = reminder.organization.telegram_chat_id
        if chat_id is None:
            raise TelegramChatNotLinkedError(
                "У организации не привязан Telegram-чат. Получите код через "
                "POST /api/organizations/me/telegram-link-code и отправьте боту "
                "команду /start <код>."
            )

        label = _TYPE_LABELS.get(reminder.type, "Напоминание")
        text = f"{label}\nДата: {reminder.target_date.isoformat()}"

        response = httpx.post(
            f"{self.api_base}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Ошибка отправки через Telegram Bot API: {data}")
        return data["result"]["message_id"]


def get_reminder_sender() -> ReminderSender:
    provider = (settings.telegram_provider or "console").strip().lower()
    if provider in ("", "console", "mock"):
        return ConsoleReminderSender()
    if provider == "telegram":
        if not settings.telegram_bot_token:
            raise RuntimeError(
                "TELEGRAM_PROVIDER=telegram требует заполненного TELEGRAM_BOT_TOKEN в .env"
            )
        return TelegramReminderSender(settings.telegram_bot_token)
    raise RuntimeError(f"Неизвестный TELEGRAM_PROVIDER: {settings.telegram_provider!r}")

"""
Абстракция над SMS-агрегатором.

Окончательный провайдер пользователем ещё не выбран (варианты из ТЗ: SMS.ru,
Devino, SMSC — см. README.md, раздел "Открытые вопросы"). SmsRuSender —
реализация под SMS.ru как разумный дефолт (самый распространённый агрегатор
в РФ, простой HTTP API), но смена провайдера — это просто ещё один класс
ниже плюс ветка в get_sms_sender().

Для локальной разработки/тестов используется ConsoleSmsSender
(SMS_PROVIDER=console или не задан) — код просто логируется, а не
отправляется реально.
"""

import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings

logger = logging.getLogger("app.sms")


class SmsSender(ABC):
    @abstractmethod
    def send(self, phone: str, code: str) -> None:
        """Отправить код подтверждения на номер телефона."""


class ConsoleSmsSender(SmsSender):
    """Заглушка для разработки и тестов — код попадает только в лог."""

    def send(self, phone: str, code: str) -> None:
        logger.info("[SMS mock] Код для %s: %s", phone, code)


class SmsRuSender(SmsSender):
    """Отправка через HTTP API SMS.ru (https://sms.ru/api/send)."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def send(self, phone: str, code: str) -> None:
        response = httpx.get(
            "https://sms.ru/sms/send",
            params={
                "api_id": self.api_key,
                "to": phone,
                "msg": f"Код подтверждения РТО-аналитика: {code}",
                "json": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") != "OK":
            raise RuntimeError(f"Ошибка отправки SMS через SMS.ru: {data}")


def get_sms_sender() -> SmsSender:
    provider = (settings.sms_provider or "console").strip().lower()
    if provider in ("", "console", "mock"):
        return ConsoleSmsSender()
    if provider in ("smsru", "sms.ru"):
        if not settings.sms_api_key:
            raise RuntimeError(
                "SMS_PROVIDER=smsru требует заполненного SMS_API_KEY в .env"
            )
        return SmsRuSender(settings.sms_api_key)
    # TODO: добавить реализации под Devino/SMSC при выборе пользователем.
    raise RuntimeError(f"Неизвестный SMS_PROVIDER: {settings.sms_provider!r}")

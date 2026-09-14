"""Вебхук для приёма апдейтов от Telegram-бота.

Сейчас обрабатывается только /start <код> — привязка чата организации (см.
app/services/telegram_link.py). Заготовка под будущие команды бота
(например, ответ на напоминание, отписку и т.п.).
"""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.telegram_link import TelegramLinkError, consume_link_code

logger = logging.getLogger("app.telegram")

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/webhook")
def telegram_webhook(update: dict, db: Session = Depends(get_db)):
    """Принимает Update от Telegram Bot API.

    Telegram повторяет доставку апдейта, если вебхук не ответил 200 — поэтому
    ошибки привязки не поднимаются как HTTP-ошибки, а только логируются, и
    эндпоинт всегда отвечает {"ok": true}.
    """
    message = update.get("message") or update.get("edited_message") or {}
    text = (message.get("text") or "").strip()
    chat_id = (message.get("chat") or {}).get("id")

    if chat_id is not None and text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) == 2:
            code = parts[1].strip()
            try:
                consume_link_code(db, code, chat_id)
                logger.info("Чат %s привязан к организации по коду", chat_id)
            except TelegramLinkError as exc:
                logger.info("Неудачная попытка привязки чата %s: %s", chat_id, exc)
        else:
            logger.info("Команда /start от чата %s без кода", chat_id)

    return {"ok": True}

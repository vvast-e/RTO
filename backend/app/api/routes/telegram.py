"""Вебхук для приёма апдейтов от Telegram-бота.

Сейчас обрабатывается только /start <код> — привязка чата организации (см.
app/services/telegram_link.py). Заготовка под будущие команды бота
(например, ответ на напоминание, отписку и т.п.).

Безопасность: без проверки источника этот эндпоинт был бы открытым оракулом
для подбора кода привязки (POST с произвольным chat_id/кодом привязал бы
чужой Telegram-чат к организации). Telegram поддерживает секретный токен
вебхука (передаётся при регистрации через setWebhook?secret_token=...,
проверяется по заголовку X-Telegram-Bot-Api-Secret-Token) — если
TELEGRAM_WEBHOOK_SECRET задан в .env, запрос без совпадающего заголовка
отклоняется 401 до того, как тело будет разобрано. Плюс — грубый
rate-limit по IP как защита от подбора, если секрет всё же не настроен
(например, на раннем этапе локальной разработки).
"""

import logging
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.telegram_link import TelegramLinkError, consume_link_code

logger = logging.getLogger("app.telegram")

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 20
_request_log: dict[str, deque] = defaultdict(deque)


def _check_rate_limit(client_ip: str) -> None:
    now = time.monotonic()
    log = _request_log[client_ip]
    while log and now - log[0] > RATE_LIMIT_WINDOW_SECONDS:
        log.popleft()
    if len(log) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Слишком много запросов к вебхуку, попробуйте позже",
        )
    log.append(now)


@router.post("/webhook")
def telegram_webhook(
    update: dict,
    request: Request,
    db: Session = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Принимает Update от Telegram Bot API.

    Telegram повторяет доставку апдейта, если вебхук не ответил 200 — поэтому
    ошибки привязки не поднимаются как HTTP-ошибки, а только логируются, и
    эндпоинт всегда отвечает {"ok": true} (за исключением провала проверки
    подлинности запроса — там честные 401/429).
    """
    if settings.telegram_webhook_secret:
        if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный секретный токен вебхука",
            )
    else:
        # Секрет не настроен (например, локальная разработка без публичного
        # HTTPS) — оставляем только rate-limit как минимальную защиту от
        # перебора кодов привязки.
        client_ip = request.client.host if request.client else "unknown"
        _check_rate_limit(client_ip)

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

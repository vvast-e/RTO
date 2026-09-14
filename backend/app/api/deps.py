"""
Общие FastAPI-зависимости.

TODO: заменить get_current_organization_id на реальную проверку JWT
(access-токен, полученный после логина по SMS-коду). Пока — заглушка,
читающая organization_id из заголовка X-Organization-Id, чтобы можно было
разрабатывать и тестировать CRUD-эндпоинты без готовой аутентификации.
"""

import uuid

from fastapi import Header, HTTPException, status


def get_current_organization_id(
    x_organization_id: str = Header(..., alias="X-Organization-Id"),
) -> uuid.UUID:
    try:
        return uuid.UUID(x_organization_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный X-Organization-Id",
        )

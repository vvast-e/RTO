"""Проверка статуса/лимита подписки при создании ресурсов, привязанных к плану.

Реальная интеграция с ЮKassa (создание платежа, вебхук подтверждения,
автосписание) — отдельный будущий этап, требующий реальных ключей провайдера
(по аналогии с TELEGRAM_PROVIDER=telegram, см. память проекта, тринадцатая
сессия). Здесь — только применение уже сохранённых plan/status/vehicles_limit,
которые пока проставляются вручную через PATCH /api/subscriptions/me."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.subscription import Subscription, SubscriptionStatus
from app.models.vehicle import Vehicle


class SubscriptionBlockedError(Exception):
    """Создание ресурса заблокировано: подписка не найдена, истекла или лимит исчерпан.

    Роуты ловят это исключение и превращают в HTTP 402 Payment Required —
    выбран вместо 403, т.к. причина отказа именно в состоянии оплаты/плана,
    а не в правах пользователя."""


def get_subscription(db: Session, organization_id: uuid.UUID) -> Subscription | None:
    return db.execute(
        select(Subscription).where(Subscription.organization_id == organization_id)
    ).scalar_one_or_none()


def count_vehicles(db: Session, organization_id: uuid.UUID) -> int:
    return db.execute(
        select(func.count()).select_from(Vehicle).where(Vehicle.organization_id == organization_id)
    ).scalar_one()


def ensure_subscription_active(db: Session, organization_id: uuid.UUID) -> Subscription:
    """Общая проверка для создания Vehicle/Driver: подписка должна существовать и
    не быть истёкшей (status=expired). Организация без Subscription не должна
    возникать после авто-создания trial-подписки при регистрации (см.
    auth_service.register_organization), но на случай рассинхронизации данных
    трактуем отсутствие подписки как блокировку — безопасный дефолт: не
    пропускать создание вслепую при отсутствующих данных о лимите."""
    subscription = get_subscription(db, organization_id)
    if subscription is None:
        raise SubscriptionBlockedError("Подписка организации не найдена, обратитесь в поддержку")
    if subscription.status == SubscriptionStatus.expired:
        raise SubscriptionBlockedError(
            "Подписка истекла, создание новых записей недоступно — продлите подписку"
        )
    return subscription


def ensure_can_create_vehicle(db: Session, organization_id: uuid.UUID) -> Subscription:
    """Проверка для POST /api/vehicles: активная подписка и лимит автомобилей
    по плану ещё не исчерпан."""
    subscription = ensure_subscription_active(db, organization_id)
    if count_vehicles(db, organization_id) >= subscription.vehicles_limit:
        raise SubscriptionBlockedError(
            f"Достигнут лимит автомобилей по текущему плану ({subscription.vehicles_limit}), "
            "обновите подписку"
        )
    return subscription

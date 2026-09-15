import uuid
from datetime import date

from pydantic import BaseModel

from app.models.subscription import SubscriptionPlan, SubscriptionStatus


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    plan: SubscriptionPlan
    status: SubscriptionStatus
    vehicles_limit: int
    # Не поле модели — считается запросом к Vehicle на лету (см.
    # subscription_service.count_vehicles), нужно фронту для отображения
    # "использовано X из Y".
    vehicles_used: int
    price: float
    next_billing_date: date | None


class SubscriptionUpdate(BaseModel):
    """Ручное обновление подписки — эмуляция админского апгрейда/оплаты без
    реального платёжного вебхука (см. TODO по интеграции с ЮKassa в
    subscription_service.py). Поля опциональны, обновляются через
    exclude_unset, как PATCH /api/vehicles."""

    plan: SubscriptionPlan | None = None
    status: SubscriptionStatus | None = None
    vehicles_limit: int | None = None
    price: float | None = None
    next_billing_date: date | None = None

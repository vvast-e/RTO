import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_organization_id
from app.db.session import get_db
from app.models.subscription import Subscription
from app.schemas.subscription import SubscriptionOut, SubscriptionUpdate
from app.services.subscription_service import count_vehicles, get_subscription

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


def _to_out(subscription: Subscription, vehicles_used: int) -> SubscriptionOut:
    return SubscriptionOut(
        id=subscription.id,
        plan=subscription.plan,
        status=subscription.status,
        vehicles_limit=subscription.vehicles_limit,
        vehicles_used=vehicles_used,
        price=float(subscription.price),
        next_billing_date=subscription.next_billing_date,
    )


@router.get("/me", response_model=SubscriptionOut)
def get_my_subscription(
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    subscription = get_subscription(db, org_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Подписка организации не найдена")
    return _to_out(subscription, count_vehicles(db, org_id))


@router.patch("/me", response_model=SubscriptionOut)
def update_my_subscription(
    payload: SubscriptionUpdate,
    org_id: uuid.UUID = Depends(get_current_organization_id),
    db: Session = Depends(get_db),
):
    subscription = get_subscription(db, org_id)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Подписка организации не найдена")

    vehicles_used = count_vehicles(db, org_id)
    data = payload.model_dump(exclude_unset=True)
    # Решение: нельзя занизить лимит ниже текущего количества машин в
    # организации — иначе получилась бы подписка, изначально нарушающая
    # собственный лимит, что сбивает с толку пользователя и ломает
    # инвариант "vehicles_used <= vehicles_limit", на который опирается
    # ensure_can_create_vehicle.
    if "vehicles_limit" in data and data["vehicles_limit"] < vehicles_used:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Нельзя установить лимит автомобилей ({data['vehicles_limit']}) ниже "
                f"текущего количества машин в организации ({vehicles_used})"
            ),
        )

    for field, value in data.items():
        setattr(subscription, field, value)
    db.commit()
    db.refresh(subscription)
    return _to_out(subscription, vehicles_used)

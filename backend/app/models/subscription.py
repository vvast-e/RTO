import uuid
import enum
from datetime import date

from sqlalchemy import ForeignKey, Enum, Date, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class SubscriptionPlan(str, enum.Enum):
    starter = "starter"
    pro = "pro"
    fleet = "fleet"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    trial = "trial"
    expired = "expired"


class Subscription(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id")
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(Enum(SubscriptionPlan))
    vehicles_limit: Mapped[int] = mapped_column(Integer)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.trial
    )
    yookassa_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    next_billing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    organization: Mapped["Organization"] = relationship()

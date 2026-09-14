from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import UUIDPKMixin, TimestampMixin


class Organization(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str | None] = mapped_column(String(12), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(String(20), default="starter")
    subscription_status: Mapped[str] = mapped_column(String(20), default="trial")
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="organization")
    drivers: Mapped[list["Driver"]] = relationship(back_populates="organization")

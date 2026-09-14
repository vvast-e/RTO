"""reminder autogeneration: Vehicle.next_inspection_date, Driver.license_expiry_date,
Reminder.vehicle_id/driver_id, ReminderType.driver_license_expiry

Revision ID: e7c9a2f5d1b4
Revises: d4a1e9f6c7b2
Create Date: 2026-09-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e7c9a2f5d1b4'
down_revision: Union[str, None] = 'd4a1e9f6c7b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'vehicles',
        sa.Column('next_inspection_date', sa.Date(), nullable=True),
    )
    op.add_column(
        'drivers',
        sa.Column('license_expiry_date', sa.Date(), nullable=True),
    )
    op.add_column(
        'reminders',
        sa.Column('vehicle_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vehicles.id'), nullable=True),
    )
    op.add_column(
        'reminders',
        sa.Column('driver_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('drivers.id'), nullable=True),
    )
    # Postgres 12+ разрешает ALTER TYPE ... ADD VALUE внутри транзакции, пока
    # новое значение не используется в той же транзакции — здесь оно только
    # добавляется, поэтому дополнительный autocommit-блок не нужен.
    op.execute("ALTER TYPE remindertype ADD VALUE IF NOT EXISTS 'driver_license_expiry'")


def downgrade() -> None:
    op.drop_column('reminders', 'driver_id')
    op.drop_column('reminders', 'vehicle_id')
    op.drop_column('drivers', 'license_expiry_date')
    op.drop_column('vehicles', 'next_inspection_date')
    # Postgres не поддерживает удаление значения из ENUM напрямую. Пересобираем
    # тип без 'driver_license_expiry' — сработает только если ни одна строка
    # ещё не использует это значение (ожидаемо для dev-отката сразу после
    # upgrade; для отката на проде с реальными данными нужен отдельный план
    # миграции данных, что вне скоупа этой сессии).
    bind = op.get_bind()
    op.execute("ALTER TYPE remindertype RENAME TO remindertype_old")
    new_enum = sa.Enum(
        'rto_deadline', 'etrn_deadline', 'vehicle_inspection', 'custom',
        name='remindertype',
    )
    new_enum.create(bind, checkfirst=False)
    op.execute(
        "ALTER TABLE reminders ALTER COLUMN type TYPE remindertype "
        "USING type::text::remindertype"
    )
    op.execute("DROP TYPE remindertype_old")

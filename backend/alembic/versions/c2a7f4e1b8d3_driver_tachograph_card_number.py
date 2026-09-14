"""driver tachograph card number

Revision ID: c2a7f4e1b8d3
Revises: b1962acb4489
Create Date: 2026-09-14 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c2a7f4e1b8d3'
down_revision: Union[str, None] = 'b1962acb4489'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'drivers',
        sa.Column('tachograph_card_number', sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('drivers', 'tachograph_card_number')

"""telegram chat link (organizations.telegram_chat_id + telegram_link_codes)

Revision ID: d4a1e9f6c7b2
Revises: c2a7f4e1b8d3
Create Date: 2026-09-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4a1e9f6c7b2'
down_revision: Union[str, None] = 'c2a7f4e1b8d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'organizations',
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=True),
    )
    op.create_table(
        'telegram_link_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('code', sa.String(length=16), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_telegram_link_codes_code', 'telegram_link_codes', ['code'])


def downgrade() -> None:
    op.drop_index('ix_telegram_link_codes_code', table_name='telegram_link_codes')
    op.drop_table('telegram_link_codes')
    op.drop_column('organizations', 'telegram_chat_id')

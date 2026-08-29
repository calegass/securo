"""add notes and custom cadence to recurring transactions

Revision ID: 078
Revises: 077
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "078"
down_revision: Union[str, None] = "077"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("recurring_transactions", sa.Column("notes", sa.String(length=1000), nullable=True))
    op.add_column("recurring_transactions", sa.Column("interval_count", sa.Integer(), nullable=True))
    op.add_column("recurring_transactions", sa.Column("interval_unit", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("recurring_transactions", "interval_unit")
    op.drop_column("recurring_transactions", "interval_count")
    op.drop_column("recurring_transactions", "notes")

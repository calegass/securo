"""add configurable recurring email alerts

Revision ID: 079
Revises: 078
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "079"
down_revision: Union[str, None] = "078"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "recurring_transactions",
        sa.Column("notification_offsets", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "recurring_transactions",
        sa.Column("notify_overdue_daily", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table(
        "notification_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "recurring_transaction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recurring_transactions.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "credit_card_bill_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("credit_card_bills.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("alert_type", sa.String(length=20), nullable=False),
        sa.Column("sent_on", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "recurring_transaction_id",
            "occurrence_date",
            "alert_type",
            "sent_on",
            name="uq_recurring_notification_delivery",
        ),
        sa.UniqueConstraint(
            "credit_card_bill_id",
            "occurrence_date",
            "alert_type",
            "sent_on",
            name="uq_card_bill_notification_delivery",
        ),
    )
    op.create_index("ix_notification_deliveries_user_id", "notification_deliveries", ["user_id"])
    op.create_index(
        "ix_notification_deliveries_recurring_transaction_id",
        "notification_deliveries",
        ["recurring_transaction_id"],
    )
    op.create_index(
        "ix_notification_deliveries_credit_card_bill_id",
        "notification_deliveries",
        ["credit_card_bill_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_deliveries_credit_card_bill_id", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_recurring_transaction_id", table_name="notification_deliveries")
    op.drop_index("ix_notification_deliveries_user_id", table_name="notification_deliveries")
    op.drop_table("notification_deliveries")
    op.drop_column("recurring_transactions", "notify_overdue_daily")
    op.drop_column("recurring_transactions", "notification_offsets")

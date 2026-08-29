import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.transaction import Transaction
    from app.models.user import User


class RecurringTransaction(Base):
    __tablename__ = "recurring_transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "description", "frequency", "start_date", name="uq_recurring_tx"),
        CheckConstraint(
            "weekend_adjustment IN ('none', 'previous_friday', 'next_monday')",
            name="ck_recurring_transactions_weekend_adjustment",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    type: Mapped[str] = mapped_column(String(10))  # debit, credit
    frequency: Mapped[str] = mapped_column(String(20))  # weekly, monthly, quarterly, yearly, custom
    # Custom cadence is intentionally generic (e.g. every 15 days or every
    # 2 months). Built-in frequencies keep these NULL for compatibility.
    interval_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interval_unit: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    weekend_adjustment: Mapped[str] = mapped_column(
        String(20), default="none", server_default="none"
    )
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # When True (the default), generate_pending materializes this bill's due
    # occurrences into real transactions. When False, no placeholder is written
    # and the bill is only shown as a projection until the actual charge is
    # matched to it (e.g. from bank sync). Either way, incoming real
    # transactions are linked back to the bill to avoid duplicates.
    auto_generate: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Negative values are days before the due date; zero is the due date.
    # An empty list disables emails for this obligation.
    notification_offsets: Mapped[list[int]] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    notify_overdue_daily: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    next_occurrence: Mapped[date] = mapped_column(Date)
    amount_primary: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    fx_rate_used: Mapped[Optional[Decimal]] = mapped_column(Numeric(precision=20, scale=10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship()
    account: Mapped[Optional["Account"]] = relationship()
    category: Mapped[Optional["Category"]] = relationship()
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="recurring_transaction"
    )

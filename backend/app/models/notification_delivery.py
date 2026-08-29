import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

class NotificationDelivery(Base):
    """Idempotency record for a notification sent for a recurring occurrence."""

    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint(
            "recurring_transaction_id",
            "occurrence_date",
            "alert_type",
            "sent_on",
            name="uq_recurring_notification_delivery",
        ),
        UniqueConstraint(
            "credit_card_bill_id",
            "occurrence_date",
            "alert_type",
            "sent_on",
            name="uq_card_bill_notification_delivery",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    recurring_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("recurring_transactions.id", ondelete="CASCADE"), index=True, nullable=True
    )
    credit_card_bill_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("credit_card_bills.id", ondelete="CASCADE"), index=True, nullable=True
    )
    occurrence_date: Mapped[date] = mapped_column(Date)
    alert_type: Mapped[str] = mapped_column(String(20))  # before, due, overdue
    sent_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

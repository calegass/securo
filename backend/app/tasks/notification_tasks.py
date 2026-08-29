"""Scheduled, idempotent email alerts for recurring financial obligations."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.credit_card_bill import CreditCardBill
from app.models.notification_delivery import NotificationDelivery
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.user import User
from app.services.notification_service import send_email
from app.services.recurring_transaction_service import get_occurrences_in_range
from app.worker import celery_app

logger = logging.getLogger(__name__)

CARD_BILL_NOTIFICATION_OFFSETS = frozenset({-3, 0})


def _make_session_maker():
    engine = create_async_engine(get_settings().database_url)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _today_for_user(user: User, now: datetime | None = None) -> date:
    """Resolve a notification date in the user's configured IANA timezone."""
    preferences = user.preferences or {}
    timezone_name = preferences.get("timezone", "UTC")
    try:
        user_timezone = ZoneInfo(timezone_name)
    except (TypeError, ZoneInfoNotFoundError):
        logger.warning("Invalid timezone %r for user %s; using UTC", timezone_name, user.id)
        user_timezone = timezone.utc
    return (now or datetime.now(timezone.utc)).astimezone(user_timezone).date()


async def _already_sent(
    session: AsyncSession,
    recurring_id,
    occurrence: date,
    alert_type: str,
    today: date,
) -> bool:
    return await session.scalar(
        select(NotificationDelivery.id).where(
            NotificationDelivery.recurring_transaction_id == recurring_id,
            NotificationDelivery.occurrence_date == occurrence,
            NotificationDelivery.alert_type == alert_type,
            NotificationDelivery.sent_on == today,
        )
    ) is not None


async def _record_delivery(
    session: AsyncSession,
    recurring: RecurringTransaction,
    occurrence: date,
    alert_type: str,
    today: date,
) -> bool:
    session.add(
        NotificationDelivery(
            user_id=recurring.user_id,
            recurring_transaction_id=recurring.id,
            occurrence_date=occurrence,
            alert_type=alert_type,
            sent_on=today,
        )
    )
    try:
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False


async def _send_credit_card_bill_alert(
    session: AsyncSession, user: User, bill: CreditCardBill, today: date
) -> bool:
    delta = (today - bill.due_date).days
    if delta not in CARD_BILL_NOTIFICATION_OFFSETS:
        return False
    alert_type = "due" if delta == 0 else "before"
    already_sent = await session.scalar(
        select(NotificationDelivery.id).where(
            NotificationDelivery.credit_card_bill_id == bill.id,
            NotificationDelivery.occurrence_date == bill.due_date,
            NotificationDelivery.alert_type == alert_type,
            NotificationDelivery.sent_on == today,
        )
    )
    if already_sent is not None:
        return False

    due = bill.due_date.strftime("%d/%m/%Y")
    if alert_type == "due":
        subject = f"{get_settings().app_name}: fatura vence hoje"
        body = f"Sua fatura de cartão vence hoje ({due}): {bill.total_amount} {bill.currency}."
    else:
        subject = f"{get_settings().app_name}: fatura vence em 3 dias"
        body = f"Sua fatura de cartão vence em {due}: {bill.total_amount} {bill.currency}."
    if not await send_email(user.email, subject, body):
        return False

    session.add(
        NotificationDelivery(
            user_id=bill.user_id,
            credit_card_bill_id=bill.id,
            occurrence_date=bill.due_date,
            alert_type=alert_type,
            sent_on=today,
        )
    )
    try:
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        return False


async def _is_paid(session: AsyncSession, recurring: RecurringTransaction, occurrence: date) -> bool:
    return await session.scalar(
        select(Transaction.id).where(
            Transaction.recurring_transaction_id == recurring.id,
            Transaction.date == occurrence,
            Transaction.status == "posted",
        )
    ) is not None


async def _send_recurring_alert(
    session: AsyncSession,
    user: User,
    recurring: RecurringTransaction,
    occurrence: date,
    alert_type: str,
    today: date,
) -> bool:
    if await _already_sent(session, recurring.id, occurrence, alert_type, today):
        return False
    if alert_type == "overdue" and await _is_paid(session, recurring, occurrence):
        return False

    when = occurrence.strftime("%d/%m/%Y")
    if alert_type == "before":
        subject = f"{get_settings().app_name}: vencimento próximo — {recurring.description}"
        body = f"{recurring.description} vence em {when}: {recurring.amount} {recurring.currency}."
    elif alert_type == "due":
        subject = f"{get_settings().app_name}: vence hoje — {recurring.description}"
        body = f"{recurring.description} vence hoje: {recurring.amount} {recurring.currency}."
    else:
        subject = f"{get_settings().app_name}: vencida — {recurring.description}"
        body = f"{recurring.description} venceu em {when}: {recurring.amount} {recurring.currency}."

    if not await send_email(user.email, subject, body):
        return False
    return await _record_delivery(session, recurring, occurrence, alert_type, today)


async def _send_due_alerts() -> int:
    engine, session_maker = _make_session_maker()
    try:
        sent = 0
        async with session_maker() as session:
            recurring_rows = list(
                (
                    await session.execute(
                        select(RecurringTransaction, User)
                        .join(User, User.id == RecurringTransaction.user_id)
                        .where(RecurringTransaction.is_active == True)
                    )
                ).all()
            )
            for recurring, user in recurring_rows:
                today = _today_for_user(user)
                offsets = recurring.notification_offsets or []
                if not offsets and not recurring.notify_overdue_daily:
                    continue
                max_advance = max((-offset for offset in offsets), default=0)
                occurrences = get_occurrences_in_range(
                    start=recurring.start_date,
                    frequency=recurring.frequency,
                    end_date=recurring.end_date,
                    range_start=today - timedelta(days=31),
                    range_end=today + timedelta(days=max_advance + 1),
                    intended_day=recurring.day_of_month or recurring.start_date.day,
                    weekend_adjustment=recurring.weekend_adjustment,
                    interval_count=recurring.interval_count,
                    interval_unit=recurring.interval_unit,
                )
                for occurrence in occurrences:
                    delta = (today - occurrence).days
                    if delta <= 0 and -delta in offsets:
                        alert_type = "due" if delta == 0 else "before"
                    elif delta > 0 and recurring.notify_overdue_daily:
                        alert_type = "overdue"
                    else:
                        continue
                    if await _send_recurring_alert(
                        session, user, recurring, occurrence, alert_type, today
                    ):
                        sent += 1
            bills = list(
                (
                    await session.execute(
                        select(CreditCardBill, User)
                        .join(User, User.id == CreditCardBill.user_id)
                        .where(
                            CreditCardBill.due_date >= datetime.now(timezone.utc).date() - timedelta(days=1),
                            CreditCardBill.due_date <= datetime.now(timezone.utc).date() + timedelta(days=4),
                        )
                    )
                ).all()
            )
            for bill, user in bills:
                today = _today_for_user(user)
                if await _send_credit_card_bill_alert(session, user, bill, today):
                    sent += 1
        return sent
    finally:
        await engine.dispose()


@celery_app.task(name="app.tasks.notification_tasks.send_due_alerts")
def send_due_alerts() -> dict:
    sent = asyncio.run(_send_due_alerts())
    logger.info("Financial due-alert run complete: %d emails sent", sent)
    return {"sent": sent}

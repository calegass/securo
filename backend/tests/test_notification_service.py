from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.credit_card_bill import CreditCardBill
from app.models.notification_delivery import NotificationDelivery
from app.models.recurring_transaction import RecurringTransaction
from app.services.notification_service import EmailNotificationProvider, NotificationMessage
from app.tasks.notification_tasks import (
    _send_credit_card_bill_alert,
    _send_recurring_alert,
    _today_for_user,
)


async def test_email_provider_is_a_safe_noop_without_smtp(monkeypatch):
    provider = EmailNotificationProvider()
    provider.settings = provider.settings.model_copy(update={"smtp_host": "", "smtp_from": ""})

    called = False

    def should_not_send(_: NotificationMessage) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(provider, "_send_blocking", should_not_send)

    assert await provider.send(NotificationMessage("person@example.com", "Subject", "Body")) is False
    assert called is False


async def test_email_provider_delegates_to_smtp_adapter(monkeypatch):
    provider = EmailNotificationProvider()
    provider.settings = provider.settings.model_copy(
        update={"smtp_host": "smtp.example.com", "smtp_from": "Securo <notifications@example.com>"}
    )
    delivered: list[NotificationMessage] = []

    monkeypatch.setattr(provider, "_send_blocking", delivered.append)

    message = NotificationMessage("person@example.com", "Subject", "Body")
    assert await provider.send(message) is True
    assert delivered == [message]


@pytest.mark.asyncio
async def test_recurring_alert_is_delivered_once_per_day(
    session: AsyncSession, test_user, test_workspace, monkeypatch
):
    account = Account(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Conta",
        type="checking",
        balance=Decimal("0"),
        currency="BRL",
    )
    recurring = RecurringTransaction(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        account=account,
        description="Internet",
        amount=Decimal("119"),
        currency="BRL",
        type="debit",
        frequency="monthly",
        start_date=date(2026, 9, 10),
        next_occurrence=date(2026, 9, 10),
        notification_offsets=[-3, 0],
    )
    session.add(recurring)
    await session.commit()

    sent: list[tuple[str, str, str]] = []

    async def fake_send_email(recipient: str | None, subject: str, body: str) -> bool:
        sent.append((recipient or "", subject, body))
        return True

    monkeypatch.setattr("app.tasks.notification_tasks.send_email", fake_send_email)
    today = date(2026, 9, 7)

    assert await _send_recurring_alert(session, test_user, recurring, date(2026, 9, 10), "before", today)
    assert not await _send_recurring_alert(session, test_user, recurring, date(2026, 9, 10), "before", today)
    assert len(sent) == 1
    deliveries = (await session.execute(select(NotificationDelivery))).scalars().all()
    assert len(deliveries) == 1


@pytest.mark.asyncio
async def test_credit_card_bill_alert_is_delivered_once_per_day(
    session: AsyncSession, test_user, test_workspace, monkeypatch
):
    account = Account(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        name="Cartão",
        type="credit_card",
        balance=Decimal("0"),
        currency="BRL",
    )
    session.add(account)
    await session.flush()
    bill = CreditCardBill(
        user_id=test_user.id,
        workspace_id=test_workspace.id,
        account_id=account.id,
        external_id="statement-2026-09",
        due_date=date(2026, 9, 10),
        total_amount=Decimal("834"),
        currency="BRL",
    )
    session.add(bill)
    await session.commit()

    async def fake_send_email(*_args) -> bool:
        return True

    monkeypatch.setattr("app.tasks.notification_tasks.send_email", fake_send_email)
    today = date(2026, 9, 7)
    assert await _send_credit_card_bill_alert(session, test_user, bill, today)
    assert not await _send_credit_card_bill_alert(session, test_user, bill, today)


def test_notification_date_uses_user_timezone(test_user):
    test_user.preferences = {"timezone": "America/Sao_Paulo"}
    now = datetime(2026, 9, 10, 0, 30, tzinfo=timezone.utc)
    assert _today_for_user(test_user, now) == date(2026, 9, 9)

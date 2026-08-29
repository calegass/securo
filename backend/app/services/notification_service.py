"""Domain-facing notifications with an optional SMTP delivery adapter."""
from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotificationMessage:
    recipient: str
    subject: str
    body: str


class EmailNotificationProvider:
    """Small SMTP adapter; application code only deals in messages."""

    def __init__(self) -> None:
        self.settings = get_settings()

    @property
    def is_configured(self) -> bool:
        return bool(self.settings.smtp_host and self.settings.smtp_from)

    def _send_blocking(self, message: NotificationMessage) -> None:
        email = EmailMessage()
        email["From"] = self.settings.smtp_from
        email["To"] = message.recipient
        email["Subject"] = message.subject
        email.set_content(message.body)

        with smtplib.SMTP(
            self.settings.smtp_host,
            self.settings.smtp_port,
            timeout=self.settings.smtp_timeout_seconds,
        ) as client:
            client.ehlo()
            if self.settings.smtp_tls:
                client.starttls()
                client.ehlo()
            if self.settings.smtp_username:
                client.login(
                    self.settings.smtp_username,
                    self.settings.smtp_password.get_secret_value(),
                )
            client.send_message(email)

    async def send(self, message: NotificationMessage) -> bool:
        if not self.is_configured:
            return False
        try:
            await asyncio.to_thread(self._send_blocking, message)
            return True
        except Exception:
            # Notifications must not turn a bank sync failure into a worker
            # failure, nor leak SMTP credentials through an exception string.
            logger.exception("Email notification delivery failed")
            return False


async def send_email(recipient: str | None, subject: str, body: str) -> bool:
    """Best-effort notification entry point for domain services and jobs."""
    if not recipient:
        return False
    return await EmailNotificationProvider().send(
        NotificationMessage(recipient=recipient, subject=subject, body=body)
    )

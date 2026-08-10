"""SMTP delivery for invitations and password-reset messages."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Small async wrapper around the configured SMTP relay."""

    async def send_invitation(self, *, email: str, name: str, token: str) -> bool:
        link = f"{settings.web_base_url.rstrip('/')}/accept-invitation?token={token}"
        return await self._send(
            recipient=email,
            subject="一站式智能招投标平台账户邀请",
            body=f"{name}，您好：\n\n请打开以下链接完成账户激活：\n{link}\n\n链接将在 24 小时后失效。",
        )

    async def send_password_reset(self, *, email: str, name: str, token: str) -> bool:
        link = f"{settings.web_base_url.rstrip('/')}/reset-password?token={token}"
        return await self._send(
            recipient=email,
            subject="一站式智能招投标平台密码重置",
            body=f"{name}，您好：\n\n请打开以下链接设置新密码：\n{link}\n\n链接将在 30 分钟后失效。",
        )

    async def _send(self, *, recipient: str, subject: str, body: str) -> bool:
        message = EmailMessage()
        message["From"] = settings.mail_from
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)

        try:
            await asyncio.to_thread(self._send_sync, message)
        except (OSError, smtplib.SMTPException):
            logger.exception("email_delivery_failed", extra={"recipient": recipient, "subject": subject})
            return False
        return True

    @staticmethod
    def _send_sync(message: EmailMessage) -> None:
        with smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=10) as client:
            if settings.mail_use_tls:
                client.starttls()
            if settings.mail_username and settings.mail_password:
                client.login(settings.mail_username, settings.mail_password)
            client.send_message(message)

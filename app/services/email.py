"""Simple SMTP email sender service."""

from email.message import EmailMessage
from email.utils import formataddr
import smtplib
from typing import Optional

from app.config import settings


class EmailNotConfigured(Exception):
    """Raised when SMTP configuration is missing."""


def _ensure_config():
    if not (settings.SMTP_HOST and settings.SMTP_PORT and settings.SMTP_FROM):
        raise EmailNotConfigured("SMTP is not configured. Please set SMTP_HOST, SMTP_PORT, SMTP_FROM.")


def send_email(
    *,
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
) -> None:
    """Send an email using SMTP with optional plain text fallback."""
    _ensure_config()

    msg = EmailMessage()
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_FROM))
    msg["To"] = to_email
    msg["Subject"] = subject

    if text_content:
        msg.set_content(text_content)
    msg.add_alternative(html_content, subtype="html")

    if settings.SMTP_USE_TLS:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

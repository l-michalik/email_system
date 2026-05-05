from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Callable

from config.settings import load_settings


def build_message(
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    if html_body is not None:
        message.add_alternative(html_body, subtype="html")
    return message


def send_email(
    subject: str,
    body: str,
    recipient: str | None = None,
    html_body: str | None = None,
    log_message_factory: Callable[[str], str] | None = None,
) -> None:
    settings = load_settings()
    resolved_recipient = recipient or settings.default_recipient
    if resolved_recipient is None:
        raise ValueError("Missing email recipient")

    message = build_message(
        settings.smtp_from,
        resolved_recipient,
        subject,
        body,
        html_body,
    )
    context = ssl.create_default_context()
    logger = logging.getLogger(__name__)

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as client:
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as client:
            client.ehlo()
            client.starttls(context=context)
            client.ehlo()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)

    logger = logging.getLogger(__name__)
    if log_message_factory is None:
        logger.info("Email sent: subject=%s recipient=%s", subject, resolved_recipient)
        return

    logger.info(log_message_factory(resolved_recipient))


def send_test_email() -> None:
    send_email("Test email", "This is a test email sent from email_system.")

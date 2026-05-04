from __future__ import annotations

import smtplib
import ssl
import logging
from email.message import EmailMessage

from config.settings import load_settings


DEFAULT_RECIPIENT = "l.michalik004@gmail.com"
logger = logging.getLogger(__name__)


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
    recipient: str = DEFAULT_RECIPIENT,
    html_body: str | None = None,
) -> None:
    settings = load_settings()
    message = build_message(settings.smtp_from, recipient, subject, body, html_body)
    context = ssl.create_default_context()
    logger.info(
        "Connecting to SMTP host=%s port=%s recipient=%s subject=%s",
        settings.smtp_host,
        settings.smtp_port,
        recipient,
        subject,
    )

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as client:
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
        logger.info("SMTP email sent over SSL to %s", recipient)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as client:
        client.ehlo()
        client.starttls(context=context)
        client.ehlo()
        client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)
    logger.info("SMTP email sent over STARTTLS to %s", recipient)


def send_test_email() -> None:
    send_email("Test email", "This is a test email sent from email_system.")

from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from config.settings import load_settings


DEFAULT_RECIPIENT = "l.michalik004@gmail.com"


def build_message(sender: str, recipient: str, subject: str, body: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    return message


def send_email(subject: str, body: str, recipient: str = DEFAULT_RECIPIENT) -> None:
    settings = load_settings()
    message = build_message(settings.smtp_from, recipient, subject, body)
    context = ssl.create_default_context()

    if settings.smtp_port == 465:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as client:
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as client:
        client.ehlo()
        client.starttls(context=context)
        client.ehlo()
        client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


def send_test_email() -> None:
    send_email("Test email", "This is a test email sent from email_system.")

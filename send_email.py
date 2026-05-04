from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

from config.settings import load_settings


RECIPIENT = "l.michalik004@gmail.com"
SUBJECT = "Test email"
BODY = "This is a test email sent from email_system."


def build_message(sender: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = RECIPIENT
    message["Subject"] = SUBJECT
    message.set_content(BODY)
    return message


def send_test_email() -> None:
    settings = load_settings()
    message = build_message(settings.smtp_from)
    context = ssl.create_default_context()

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


def main() -> None:
    send_test_email()
    print(f"Email sent to {RECIPIENT}")


if __name__ == "__main__":
    main()

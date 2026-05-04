from config.constants import BRIEF_EMAIL_SUBJECT
from utils.mailer import send_email
from utils.monitoring import (
    build_brief_creation_email_html,
    build_brief_creation_email_text,
)


def main() -> None:
    brief_number = "14993"
    send_email(
        BRIEF_EMAIL_SUBJECT,
        build_brief_creation_email_text(brief_number),
        html_body=build_brief_creation_email_html(brief_number),
    )
    print("Email sent to l.michalik004@gmail.com")


if __name__ == "__main__":
    main()

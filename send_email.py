from config.constants import BRIEF_EMAIL_SUBJECT
from utils.mailer import send_email
from utils.monitoring import build_brief_creation_email_html


def main() -> None:
    brief_id = "14993"
    body = (
        "Brief has been created successfully.\n\n"
        f"Brief ID: {brief_id}\n"
        "Chatbot link: https://waa.mdbgo.io/\n"
    )
    send_email(
        BRIEF_EMAIL_SUBJECT,
        body,
        html_body=build_brief_creation_email_html(brief_id),
    )
    print("Email sent to l.michalik004@gmail.com")


if __name__ == "__main__":
    main()

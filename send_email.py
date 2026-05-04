from utils.mailer import send_email
from utils.email_templates import build_email_html, build_email_text
from utils.monitoring import (
    build_email_template_content,
)


def main() -> None:
    brief_id = "14993"
    content = build_email_template_content("change_request_updated", brief_id)
    send_email(
        content.subject,
        build_email_text(content),
        html_body=build_email_html(content),
    )
    print("Email sent to l.michalik004@gmail.com")


if __name__ == "__main__":
    main()

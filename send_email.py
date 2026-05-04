from services.monitoring import (
    send_brief_creation_email,
    send_change_request_updated_email,
)


def main() -> None:
    brief_id = "14993"
    # send_brief_creation_email(brief_id)
    send_change_request_updated_email(brief_id)
    print("Email sent to l.michalik004@gmail.com")


if __name__ == "__main__":
    main()

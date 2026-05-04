from services.monitoring import (
    send_brief_creation_email,
    send_change_request_updated_email,
    send_work_review_request_email,
)


def main() -> None:
    brief_id = "14993"
    brief_number = "12345"
    job_name = "Example Job Name"
    job_number = "67890"
    # send_brief_creation_email(brief_id)
    # send_change_request_updated_email(brief_id)
    # send_work_review_request_email(brief_number, job_name, job_number)
    print("Email sent to l.michalik004@gmail.com")


if __name__ == "__main__":
    main()

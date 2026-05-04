from utils.mailer import send_test_email


def main() -> None:
    send_test_email()
    print("Email sent to l.michalik004@gmail.com")


if __name__ == "__main__":
    main()

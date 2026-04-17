from email.utils import parseaddr

from google_client import get_google_services

from gmail_reader import get_unprocessed_message_ids, get_message_by_id
from gmail_writer import send_reply
from gmail_actions import get_or_create_label, mark_as_processed
from sms_sender_code import send_sms
from daily_log import log_report_entry


def main():
    print("Connecting to Google services...")

    gmail_service, _ = get_google_services()

    message_ids = get_unprocessed_message_ids(gmail_service)

    if not message_ids:
        print("No unread emails found.")
        return

    processed_label_id = get_or_create_label(gmail_service, "PROCESSED")

    for msg_id in message_ids:
        message = get_message_by_id(gmail_service, msg_id)

        print("=== EMAIL OUTPUT ===")
        print(f"ID: {message['id']}")
        print(f"Thread: {message['thread_id']}")
        print(f"From: {message['sender']}")
        print(f"Subject: {message['subject']}")
        print("\n--- BODY ---\n")
        print(message["body"])

        sender_email = parseaddr(message["sender"])[1]

        print("\nSending reply...\n")

        sent = send_reply(
            gmail_service=gmail_service,
            to=sender_email,
            subject=message["subject"],
            body="Thanks for your email! I'll get back to you soon.",
            thread_id=message["thread_id"],
            original_message_id_header=message["message_id_header"],
        )

        if sent:
            print("Reply sent successfully.")

            log_report_entry(
                comment=f"Replied to email from {sender_email} with subject: {message['subject']}",
                process_name="email_reply",
            )

            mark_as_processed(gmail_service, message["id"], processed_label_id)

            send_sms(
                "+14846315326",
                f"Replied to email from {sender_email} with subject: {message['subject']}",
            )

            print("Marked email as processed and sent SMS notification.")
        else:
            print("Reply failed.")


if __name__ == "__main__":
    main()
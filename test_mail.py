from datetime import datetime, timedelta
from email.utils import parseaddr

from google_client import get_google_services

from gmail_reader import get_unprocessed_message_ids, get_message_by_id
from gmail_writer import send_reply
from gmail_actions import get_or_create_label, mark_as_processed
from calendar_actions import is_time_available, create_appointment
from sms_sender_code import send_sms
from daily_log import log_report_entry


APPOINTMENT_LENGTH_MINUTES = 30


def parse_subject_for_appointment(subject: str) -> tuple[str, datetime]:
    """
    Parses a subject in the format:

    TITLE,DATE,TIME

    Example:
    Project Meeting,04/18/2026,2:30 PM

    Returns:
        (title, start_dt)

    Raises:
        ValueError if the format is invalid.
    """
    parts = [part.strip() for part in subject.split(",")]

    if len(parts) != 3:
        raise ValueError(
            "Subject must be in the format: TITLE,DATE,TIME"
        )

    title, date_str, time_str = parts

    # Expected example: 04/18/2026 and 2:30 PM
    combined = f"{date_str} {time_str}"

    try:
        start_dt = datetime.strptime(combined, "%m/%d/%Y %I:%M %p").astimezone()
    except ValueError as exc:
        raise ValueError(
            "Date/time must look like MM/DD/YYYY and HH:MM AM/PM"
        ) from exc

    return title, start_dt


def build_reply_body(is_available: bool, title: str, start_dt: datetime) -> str:
    """
    Builds the email reply body based on whether the slot is available.
    """
    friendly_time = start_dt.strftime("%A, %B %d, %Y at %I:%M %p").replace(" 0", " ")

    if is_available:
        return (
            f"That time works.\n\n"
            f"Your appointment '{title}' has been scheduled for {friendly_time}."
        )

    return (
        f"That time is not available.\n\n"
        f"Requested appointment: '{title}' on {friendly_time}.\n"
        f"Please send a different date and time."
    )


def main():
    print("Connecting to Google services...")

    gmail_service, calendar_service = get_google_services()

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

        try:
            title, start_dt = parse_subject_for_appointment(message["subject"])
            end_dt = start_dt + timedelta(minutes=APPOINTMENT_LENGTH_MINUTES)

            available = is_time_available(
                calendar_service=calendar_service,
                start_dt=start_dt,
                end_dt=end_dt,
            )

            if available:
                create_appointment(
                    calendar_service=calendar_service,
                    title=title,
                    start_dt=start_dt,
                    end_dt=end_dt,
                    description=f"Appointment requested by {sender_email}",
                    attendee_emails=[sender_email],
                )

            reply_body = build_reply_body(
                is_available=available,
                title=title,
                start_dt=start_dt,
            )

        except ValueError as exc:
            reply_body = (
                "Your subject line is not in the correct format.\n\n"
                "Please use:\n"
                "TITLE,DATE,TIME\n\n"
                "Example:\n"
                "Project Meeting,04/18/2026,2:30 PM"
            )
            print(f"Subject parse failed: {exc}")

        print("\nSending reply...\n")

        sent = send_reply(
            gmail_service=gmail_service,
            to=sender_email,
            subject=f"Re: {message['subject']}",
            body=reply_body,
            thread_id=message["thread_id"],
            original_message_id_header=message["message_id_header"],
        )

        if sent:
            print("Reply sent successfully.")

            try:
                log_report_entry(
                    comment=f"Processed email from {sender_email} with subject: {message['subject']}",
                    process_name="email_reply",
                )
            except PermissionError:
                print("Could not write to daily log because the CSV is open.")

            mark_as_processed(gmail_service, message["id"], processed_label_id)

            send_sms(
                "+14846315326",
                f"Processed email from {sender_email} with subject: {message['subject']}",
            )

            print("Marked email as processed and sent SMS notification.")
        else:
            print("Reply failed.")


if __name__ == "__main__":
    main()
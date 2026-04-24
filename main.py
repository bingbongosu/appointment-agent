import os
from email.utils import parseaddr

from dotenv import load_dotenv

from parser import parse_email
from reply_writer import write_reply
from models import AgentOutput, SlotResult

from google_client import get_google_services
from gmail_reader import get_unprocessed_message_ids, get_message_by_id
from gmail_writer import send_reply
from gmail_actions import get_or_create_label, mark_as_processed
from scheduler import generate_available_slots
from sms_sender_code import send_sms
from daily_log import log_report_entry
from calendar_actions import create_appointment, is_time_available


def main() -> None:
    load_dotenv()

    alert_phone_number = os.getenv("ALERT_PHONE_NUMBER")

    gmail_service, calendar_service = get_google_services()

    message_ids = get_unprocessed_message_ids(gmail_service)

    if not message_ids:
        print("No unprocessed emails found.")
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
        email_text = message["body"] or ""
        subject_text = message["subject"] or ""

        if not email_text and not subject_text:
            print("Email body and subject were empty. Skipping.")
            continue

        parsed = parse_email(f"Subject: {subject_text}\n\nBody: {email_text}")

        if not parsed.is_scheduling_request:
            print("Email is not a scheduling request. Skipping.")
            continue

        slot_result = generate_available_slots(
            calendar_service=calendar_service,
            request=parsed,
            days_ahead=7,
            max_slots=3,
        )

        if (
            slot_result.exact_requested_time_available
            and slot_result.exact_start
            and slot_result.exact_end
        ):
            create_appointment(
                calendar_service=calendar_service,
                title=parsed.topic or "Appointment",
                start_dt=slot_result.exact_start,
                end_dt=slot_result.exact_end,
                description=f"Appointment requested by {sender_email}",
                attendee_emails=[sender_email],
            )
        reply = write_reply(parsed, slot_result)

        result = AgentOutput(
            parsed_request=parsed,
            proposed_slots=slot_result.slots,
            reply_draft=reply,
        )

        print("\n--- Parsed Request ---")
        print(result.parsed_request.model_dump_json(indent=2))

        print("\n--- Proposed Slots ---")
        if result.proposed_slots:
            for slot in result.proposed_slots:
                print(f"- {slot}")
        else:
            print("No slots available.")

        print("\n--- Reply Draft ---")
        print(result.reply_draft)

        print("\nSending reply...\n")

        sent = send_reply(
            gmail_service=gmail_service,
            to=sender_email,
            subject=f"Re: {message['subject']}",
            body=reply,
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

            if alert_phone_number:
                send_sms(
                    alert_phone_number,
                    f"Processed email from {sender_email} with subject: {message['subject']}",
                )
                print("SMS notification sent.")
            else:
                print("No ALERT_PHONE_NUMBER found. SMS skipped.")

            print("Marked email as processed.")
        else:
            print("Reply failed. Email was not marked as processed.")


if __name__ == "__main__":
    main()
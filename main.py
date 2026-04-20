from dotenv import load_dotenv

from parser import parse_email
from reply_writer import write_reply
from models import AgentOutput

from google_client import get_google_services
from gmail_reader import get_recent_message
from scheduler import generate_available_slots


def main() -> None:
    load_dotenv()

    gmail_service, calendar_service = get_google_services()

    message = get_recent_message(gmail_service)

    if not message:
        print("No emails found.")
        return

    email_text = message["body"]

    if not email_text:
        print("Email body was empty.")
        return

    parsed = parse_email(email_text)

    if not parsed.is_scheduling_request:
        print("Email is not a scheduling request.")
        return

    slots = generate_available_slots(
        calendar_service=calendar_service,
        request=parsed,
        days_ahead=7,
        max_slots=3,
    )

    reply = write_reply(parsed, slots)

    result = AgentOutput(
        parsed_request=parsed,
        proposed_slots=slots,
        reply_draft=reply,
    )

    print("\n--- Email Metadata ---")
    print(f"From: {message['sender']}")
    print(f"Subject: {message['subject']}")

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


if __name__ == "__main__":
    main()
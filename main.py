from dotenv import load_dotenv

from parser import parse_email
from scheduler import choose_slots
from reply_writer import write_reply
from models import AgentOutput

from google_client import get_google_services
from gmail_reader import get_recent_message
from calendar_reader import get_upcoming_events
from scheduler import choose_slots, generate_available_slots


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

    events = get_upcoming_events(calendar_service, days_ahead=7)
    availability = generate_available_slots(events)
    slots = choose_slots(parsed.requested_timeframe, availability)
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
    for slot in result.proposed_slots:
        print(f"- {slot}")

    print("\n--- Reply Draft ---")
    print(result.reply_draft)


if __name__ == "__main__":
    main()
from dotenv import load_dotenv
from parser import parse_email
from scheduler import choose_slots
from reply_writer import write_reply
from sample_data import FAKE_AVAILABILITY
from models import AgentOutput


def main() -> None:
    load_dotenv()

    print("Paste the email below. Press Enter twice when finished:\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)

    email_text = "\n".join(lines).strip()

    if not email_text:
        print("No email entered.")
        return

    parsed = parse_email(email_text)
    slots = choose_slots(parsed.requested_timeframe, FAKE_AVAILABILITY)
    reply = write_reply(parsed, slots)

    result = AgentOutput(
        parsed_request=parsed,
        proposed_slots=slots,
        reply_draft=reply,
    )

    print("\n--- Parsed Request ---")
    print(result.parsed_request.model_dump_json(indent=2))

    print("\n--- Proposed Slots ---")
    for slot in result.proposed_slots:
        print(f"- {slot}")

    print("\n--- Reply Draft ---")
    print(result.reply_draft)


if __name__ == "__main__":
    main()
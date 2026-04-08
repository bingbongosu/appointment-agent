from typing import List
from models import AppointmentRequest


def write_reply(request: AppointmentRequest, slots: List[str]) -> str:
    """
    Generates a plain-English reply draft using the parsed request and proposed slots.
    """
    if not request.is_scheduling_request:
        return "This does not appear to be a scheduling email, so no meeting reply was drafted."

    greeting = "Hi"
    if request.sender_name:
        greeting = f"Hi {request.sender_name}"

    topic_line = ""
    if request.topic:
        topic_line = f" to discuss {request.topic}"

    if not slots:
        return (
            f"{greeting},\n\n"
            f"Thanks for reaching out. I’d be glad to connect{topic_line}. "
            f"I’m checking availability and will follow up with some options shortly.\n\n"
            f"Best,\nSteve"
        )

    if len(slots) == 1:
        slot_text = slots[0]
    elif len(slots) == 2:
        slot_text = f"{slots[0]} or {slots[1]}"
    else:
        slot_text = f"{slots[0]}, {slots[1]}, or {slots[2]}"

    return (
        f"{greeting},\n\n"
        f"Thanks for reaching out. I’d be happy to connect{topic_line}. "
        f"I’m available {slot_text}. Let me know what works best for you.\n\n"
        f"Best,\nSteve"
    )
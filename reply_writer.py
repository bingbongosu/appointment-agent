from typing import List
from models import AppointmentRequest, SlotResult


def write_reply(parsed: AppointmentRequest, slot_result: SlotResult) -> str:
    slots = slot_result.slots

    if slot_result.exact_requested_time_available and slots:
        return (
            f"Hi,\n\n"
            f"That time works. I have you locked in for {slots[0]} "
            f"to discuss {parsed.topic}.\n\n"
            f"Best,\n"
            f"Steve"
        )

    if slots:
        slot_text = ", ".join(slots[:-1]) + f", or {slots[-1]}" if len(slots) > 1 else slots[0]

        return (
            f"Hi,\n\n"
            f"Thanks for reaching out. I’d be happy to connect"
            f"{f' to discuss {parsed.topic}' if parsed.topic else ''}. "
            f"I’m available {slot_text}. Let me know what works best for you.\n\n"
            f"Best,\n"
            f"Steve"
        )

    return (
        f"Hi,\n\n"
        f"Thanks for reaching out. I don’t have availability that matches the requested time. "
        f"Please send over a few other options and I’ll take a look.\n\n"
        f"Best,\n"
        f"Steve"
    )
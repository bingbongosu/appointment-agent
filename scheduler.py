from typing import List


def choose_slots(requested_timeframe: str | None, availability: List[str], max_slots: int = 3) -> List[str]:
    """
    Very simple slot picker.
    Tries to loosely match words like Tuesday, Wednesday, afternoon.
    Falls back to first available slots if no match is found.
    """
    if not requested_timeframe:
        return availability[:max_slots]

    timeframe_lower = requested_timeframe.lower()
    matches = []

    for slot in availability:
        slot_lower = slot.lower()

        day_match = any(day in timeframe_lower and day in slot_lower for day in [
            "monday", "tuesday", "wednesday", "thursday", "friday"
        ])

        afternoon_match = "afternoon" in timeframe_lower and any(
            t in slot_lower for t in ["1:", "2:", "3:", "4:", "5:"]
        )

        morning_match = "morning" in timeframe_lower and any(
            t in slot_lower for t in ["9:", "10:", "11:"]
        )

        if day_match or afternoon_match or morning_match:
            matches.append(slot)

    if len(matches) >= max_slots:
        return matches[:max_slots]

    # Top off with general availability if needed
    seen = set(matches)
    for slot in availability:
        if slot not in seen:
            matches.append(slot)
        if len(matches) >= max_slots:
            break

    return matches[:max_slots]
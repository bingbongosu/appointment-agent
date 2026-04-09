from datetime import datetime, timedelta
from typing import List


WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 17
SLOT_LENGTH_MINUTES = 30


def choose_slots(requested_timeframe: str | None, availability: List[str], max_slots: int = 3) -> List[str]:
    """
    Chooses up to max_slots from a list of available slot strings.

    It loosely matches day names and broad time-of-day words like
    'morning' or 'afternoon'. If no good match is found, it falls back
    to the first available slots.
    """
    if not requested_timeframe:
        return availability[:max_slots]

    timeframe_lower = requested_timeframe.lower()
    matches = []

    for slot in availability:
        slot_lower = slot.lower()

        day_match = any(
            day in timeframe_lower and day in slot_lower
            for day in ["monday", "tuesday", "wednesday", "thursday", "friday"]
        )

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

    seen = set(matches)
    for slot in availability:
        if slot not in seen:
            matches.append(slot)
        if len(matches) >= max_slots:
            break

    return matches[:max_slots]


def parse_google_datetime(value: str) -> datetime:
    """
    Parses a Google Calendar datetime string into a Python datetime.

    Google often returns timestamps like:
    2026-04-09T14:00:00-04:00

    This helper also handles the 'Z' UTC suffix if present.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_busy(candidate_start: datetime, candidate_end: datetime, events: List[dict]) -> bool:
    """
    Returns True if the candidate slot overlaps any calendar event.
    """
    for event in events:
        start_raw = event.get("start", {}).get("dateTime")
        end_raw = event.get("end", {}).get("dateTime")

        # Skip all-day events for now.
        # You can handle them later if needed.
        if not start_raw or not end_raw:
            continue

        event_start = parse_google_datetime(start_raw)
        event_end = parse_google_datetime(end_raw)

        overlaps = candidate_start < event_end and candidate_end > event_start
        if overlaps:
            return True

    return False


def format_slot(dt: datetime) -> str:
    """
    Formats a datetime into a human-friendly slot string.

    Example:
    Tuesday 2:00 PM
    """
    return dt.strftime("%A %I:%M %p").replace(" 0", " ")


def generate_available_slots(events: List[dict], days_ahead: int = 5, max_slots: int = 20) -> List[str]:
    """
    Generates available 30-minute slots during work hours over the next few days,
    excluding times that overlap with existing Google Calendar events.

    Assumptions:
    - Work hours are 9:00 AM to 5:00 PM
    - Slots are 30 minutes
    - Only weekdays are considered
    """
    now = datetime.now().astimezone()
    slots: List[str] = []

    for day_offset in range(days_ahead):
        current_day = (now + timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Skip weekends
        if current_day.weekday() >= 5:
            continue

        day_start = current_day.replace(hour=WORKDAY_START_HOUR)
        day_end = current_day.replace(hour=WORKDAY_END_HOUR)

        candidate_start = day_start

        while candidate_start < day_end:
            candidate_end = candidate_start + timedelta(minutes=SLOT_LENGTH_MINUTES)

            # Do not offer slots in the past
            if candidate_start <= now:
                candidate_start = candidate_end
                continue

            if not is_busy(candidate_start, candidate_end, events):
                slots.append(format_slot(candidate_start))

            if len(slots) >= max_slots:
                return slots

            candidate_start = candidate_end

    return slots
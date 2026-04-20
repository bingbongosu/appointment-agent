from datetime import datetime, timedelta
from typing import List, Optional

from models import AppointmentRequest


# =========================
# GLOBAL CONFIG
# =========================

WORKDAY_START_HOUR = 9
WORKDAY_END_HOUR = 17
SLOT_LENGTH_MINUTES = 30
LOOKAHEAD_DAYS = 7
CALENDAR_ID = "primary"

DAY_NAME_TO_NUMBER = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def parse_google_datetime(value: str) -> datetime:
    """
    Parses a Google Calendar datetime string into a timezone-aware datetime.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_time_string(value: Optional[str]) -> Optional[tuple[int, int]]:
    """
    Converts a HH:MM string into (hour, minute).

    Example:
    '14:30' -> (14, 30)
    """
    if not value:
        return None

    try:
        hour_str, minute_str = value.split(":")
        return int(hour_str), int(minute_str)
    except (ValueError, AttributeError):
        return None


def format_slot(dt: datetime) -> str:
    """
    Formats a datetime into a human-friendly slot string.

    Example:
    Tuesday 2:00 PM
    """
    return dt.strftime("%A %I:%M %p").replace(" 0", " ")


def fetch_calendar_events(
    calendar_service,
    start_dt: datetime,
    end_dt: datetime,
    calendar_id: str = CALENDAR_ID,
) -> List[dict]:
    """
    Pulls events from Google Calendar within the requested time window.
    """
    events: List[dict] = []
    page_token = None

    while True:
        response = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True,
            orderBy="startTime",
            pageToken=page_token,
        ).execute()

        events.extend(response.get("items", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return events


def is_busy(candidate_start: datetime, candidate_end: datetime, events: List[dict]) -> bool:
    """
    Returns True if the candidate slot overlaps any event.
    """
    for event in events:
        start_info = event.get("start", {})
        end_info = event.get("end", {})

        if "dateTime" in start_info and "dateTime" in end_info:
            event_start = parse_google_datetime(start_info["dateTime"])
            event_end = parse_google_datetime(end_info["dateTime"])

        elif "date" in start_info and "date" in end_info:
            event_start = datetime.fromisoformat(start_info["date"]).astimezone()
            event_end = datetime.fromisoformat(end_info["date"]).astimezone()

        else:
            continue

        if candidate_start < event_end and candidate_end > event_start:
            return True

    return False


def get_preferred_days(request: AppointmentRequest) -> set[int]:
    """
    Converts preferred_days from strings to weekday numbers.
    """
    if not request.preferred_days:
        return set()

    return {
        DAY_NAME_TO_NUMBER[day.lower()]
        for day in request.preferred_days
        if day.lower() in DAY_NAME_TO_NUMBER
    }


def get_excluded_days(request: AppointmentRequest) -> set[int]:
    """
    Converts excluded_days from strings to weekday numbers.
    """
    if not request.excluded_days:
        return set()

    return {
        DAY_NAME_TO_NUMBER[day.lower()]
        for day in request.excluded_days
        if day.lower() in DAY_NAME_TO_NUMBER
    }


def get_time_of_day_range(request: AppointmentRequest) -> Optional[tuple[int, int]]:
    """
    Converts preferred_time_of_day into a broad hour range.
    """
    if not request.preferred_time_of_day:
        return None

    value = request.preferred_time_of_day.lower()

    if value == "morning":
        return (9, 12)

    if value == "afternoon":
        return (12, 17)

    if value == "evening":
        return (17, 20)

    if value == "noon":
        return (12, 13)

    return None


def matches_hard_constraints(
    candidate_start: datetime,
    request: AppointmentRequest,
    preferred_days: set[int],
    excluded_days: set[int],
) -> bool:
    """
    Rejects slots that violate hard constraints.

    Hard constraints:
    - excluded day
    - specific preferred day(s), if given
    - not_before_time
    - not_after_time
    """
    weekday = candidate_start.weekday()

    if weekday in excluded_days:
        return False

    if preferred_days and weekday not in preferred_days:
        return False

    not_before = parse_time_string(request.not_before_time)
    if not_before:
        nb_hour, nb_minute = not_before
        if (candidate_start.hour, candidate_start.minute) < (nb_hour, nb_minute):
            return False

    not_after = parse_time_string(request.not_after_time)
    if not_after:
        na_hour, na_minute = not_after
        if (candidate_start.hour, candidate_start.minute) > (na_hour, na_minute):
            return False

    return True


def score_slot(
    candidate_start: datetime,
    request: AppointmentRequest,
    preferred_days: set[int],
    time_of_day_range: Optional[tuple[int, int]],
) -> int:
    """
    Scores a slot. Higher = better fit.
    """
    score = 0

    if preferred_days:
        if candidate_start.weekday() in preferred_days:
            score += 20
    else:
        score += 5

    if time_of_day_range:
        start_hour, end_hour = time_of_day_range
        if start_hour <= candidate_start.hour < end_hour:
            score += 15

    specific_time = parse_time_string(request.specific_time)
    if specific_time:
        sp_hour, sp_minute = specific_time

        # Exact match gets the biggest boost
        if (candidate_start.hour, candidate_start.minute) == (sp_hour, sp_minute):
            score += 50
        else:
            # Nearby times still get some credit
            candidate_minutes = candidate_start.hour * 60 + candidate_start.minute
            specific_minutes = sp_hour * 60 + sp_minute
            minute_diff = abs(candidate_minutes - specific_minutes)

            if minute_diff == 30:
                score += 25
            elif minute_diff == 60:
                score += 10

    return score


def generate_available_slots(
    calendar_service,
    request: AppointmentRequest,
    days_ahead: int = LOOKAHEAD_DAYS,
    max_slots: int = 3,
    workday_start_hour: int = WORKDAY_START_HOUR,
    workday_end_hour: int = WORKDAY_END_HOUR,
    slot_length_minutes: int = SLOT_LENGTH_MINUTES,
) -> List[str]:
    """
    Generates the best available meeting slots based on:
    - Google Calendar availability
    - structured scheduling preferences from AppointmentRequest
    """
    now = datetime.now().astimezone()

    search_start = now
    search_end = (now + timedelta(days=days_ahead)).replace(
        hour=23, minute=59, second=59, microsecond=0
    )

    events = fetch_calendar_events(
        calendar_service=calendar_service,
        start_dt=search_start,
        end_dt=search_end,
    )

    preferred_days = get_preferred_days(request)
    excluded_days = get_excluded_days(request)
    time_of_day_range = get_time_of_day_range(request)

    ranked_slots: List[tuple[int, datetime, str]] = []
    fallback_slots: List[tuple[datetime, str]] = []

    for day_offset in range(days_ahead + 1):
        current_day = (now + timedelta(days=day_offset)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        # Skip weekends unless explicitly requested
        if current_day.weekday() >= 5 and not preferred_days:
            continue

        day_start = current_day.replace(hour=workday_start_hour, minute=0)
        day_end = current_day.replace(hour=workday_end_hour, minute=0)

        candidate_start = day_start

        while candidate_start < day_end:
            candidate_end = candidate_start + timedelta(minutes=slot_length_minutes)

            if candidate_start <= now:
                candidate_start = candidate_end
                continue

            if is_busy(candidate_start, candidate_end, events):
                candidate_start = candidate_end
                continue

            slot_str = format_slot(candidate_start)

            if matches_hard_constraints(candidate_start, request, preferred_days, excluded_days):
                score = score_slot(candidate_start, request, preferred_days, time_of_day_range)
                ranked_slots.append((score, candidate_start, slot_str))
            else:
                # keep a backup pool in case constraints are too restrictive
                fallback_slots.append((candidate_start, slot_str))

            candidate_start = candidate_end

    ranked_slots.sort(key=lambda item: (-item[0], item[1]))
    best_slots = [slot_str for _, _, slot_str in ranked_slots[:max_slots]]

    if best_slots:
        return best_slots

    fallback_slots.sort(key=lambda item: item[0])
    return [slot_str for _, slot_str in fallback_slots[:max_slots]]
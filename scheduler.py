from datetime import datetime, timedelta
from typing import List, Optional

from models import AppointmentRequest, SlotResult


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
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_time_string(value: Optional[str]) -> Optional[tuple[int, int]]:
    if not value:
        return None

    try:
        hour_str, minute_str = value.split(":")
        return int(hour_str), int(minute_str)
    except (ValueError, AttributeError):
        return None


def format_slot(dt: datetime) -> str:
    return dt.strftime("%A %I:%M %p").replace(" 0", " ")


def fetch_calendar_events(
    calendar_service,
    start_dt: datetime,
    end_dt: datetime,
    calendar_id: str = CALENDAR_ID,
) -> List[dict]:
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
    if not request.preferred_days:
        return set()

    return {
        DAY_NAME_TO_NUMBER[day.lower()]
        for day in request.preferred_days
        if day.lower() in DAY_NAME_TO_NUMBER
    }


def get_excluded_days(request: AppointmentRequest) -> set[int]:
    if not request.excluded_days:
        return set()

    return {
        DAY_NAME_TO_NUMBER[day.lower()]
        for day in request.excluded_days
        if day.lower() in DAY_NAME_TO_NUMBER
    }


def get_time_of_day_range(request: AppointmentRequest) -> Optional[tuple[int, int]]:
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


def get_exact_requested_slot(
    request: AppointmentRequest,
    candidate_date: datetime,
    slot_length_minutes: int,
) -> Optional[tuple[datetime, datetime]]:
    specific_time = parse_time_string(request.specific_time)

    if not specific_time:
        return None

    hour, minute = specific_time

    start = candidate_date.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )

    end = start + timedelta(minutes=slot_length_minutes)

    return start, end


def matches_hard_constraints(
    candidate_start: datetime,
    request: AppointmentRequest,
    preferred_days: set[int],
    excluded_days: set[int],
) -> bool:
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

        candidate_minutes = candidate_start.hour * 60 + candidate_start.minute
        specific_minutes = sp_hour * 60 + sp_minute
        minute_diff = abs(candidate_minutes - specific_minutes)

        if minute_diff == 0:
            score += 50
        elif minute_diff == 30:
            score += 25
        elif minute_diff == 60:
            score += 10

    return score


def try_exact_requested_time(
    request: AppointmentRequest,
    events: List[dict],
    now: datetime,
    days_ahead: int,
    workday_start_hour: int,
    workday_end_hour: int,
    slot_length_minutes: int,
) -> Optional[SlotResult]:
    preferred_days = get_preferred_days(request)
    specific_time = parse_time_string(request.specific_time)

    if not preferred_days or not specific_time:
        return None

    for day_offset in range(days_ahead + 1):
        current_day = (now + timedelta(days=day_offset)).replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )

        if current_day.weekday() not in preferred_days:
            continue

        exact_slot = get_exact_requested_slot(
            request=request,
            candidate_date=current_day,
            slot_length_minutes=slot_length_minutes,
        )

        if not exact_slot:
            continue

        exact_start, exact_end = exact_slot

        if exact_start <= now:
            continue

        if exact_start.hour < workday_start_hour:
            continue

        if exact_end.hour > workday_end_hour:
            continue

        if exact_end.hour == workday_end_hour and exact_end.minute > 0:
            continue

        if is_busy(exact_start, exact_end, events):
            continue

        return SlotResult(
            slots=[format_slot(exact_start)],
            exact_requested_time_available=True,
            exact_start=exact_start,
            exact_end=exact_end,
        )

    return None


def generate_available_slots(
    calendar_service,
    request: AppointmentRequest,
    days_ahead: int = LOOKAHEAD_DAYS,
    max_slots: int = 3,
    workday_start_hour: int = WORKDAY_START_HOUR,
    workday_end_hour: int = WORKDAY_END_HOUR,
    slot_length_minutes: int = SLOT_LENGTH_MINUTES,
) -> SlotResult:
    now = datetime.now().astimezone()

    search_start = now
    search_end = (now + timedelta(days=days_ahead)).replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=0,
    )

    events = fetch_calendar_events(
        calendar_service=calendar_service,
        start_dt=search_start,
        end_dt=search_end,
    )

    exact_result = try_exact_requested_time(
        request=request,
        events=events,
        now=now,
        days_ahead=days_ahead,
        workday_start_hour=workday_start_hour,
        workday_end_hour=workday_end_hour,
        slot_length_minutes=slot_length_minutes,
    )

    if exact_result:
        return exact_result

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

        if current_day.weekday() >= 5 and current_day.weekday() not in preferred_days:
            continue

        day_start = current_day.replace(
            hour=workday_start_hour,
            minute=0,
            second=0,
            microsecond=0,
        )

        day_end = current_day.replace(
            hour=workday_end_hour,
            minute=0,
            second=0,
            microsecond=0,
        )

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

            if matches_hard_constraints(
                candidate_start=candidate_start,
                request=request,
                preferred_days=preferred_days,
                excluded_days=excluded_days,
            ):
                score = score_slot(
                    candidate_start=candidate_start,
                    request=request,
                    preferred_days=preferred_days,
                    time_of_day_range=time_of_day_range,
                )

                ranked_slots.append((score, candidate_start, slot_str))
            else:
                fallback_slots.append((candidate_start, slot_str))

            candidate_start = candidate_end

    ranked_slots.sort(key=lambda item: (-item[0], item[1]))
    best_slots = [slot_str for _, _, slot_str in ranked_slots[:max_slots]]

    if best_slots:
        return SlotResult(
            slots=best_slots,
            exact_requested_time_available=False,
        )

    fallback_slots.sort(key=lambda item: item[0])
    fallback_best_slots = [slot_str for _, slot_str in fallback_slots[:max_slots]]

    return SlotResult(
        slots=fallback_best_slots,
        exact_requested_time_available=False,
    )
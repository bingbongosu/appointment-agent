from __future__ import annotations

from datetime import datetime, timedelta
from typing import List


def to_google_datetime(dt: datetime) -> str:
    """
    Converts a Python datetime into the RFC3339 string format
    Google Calendar expects.

    Example:
    2026-04-17T14:00:00-04:00
    """
    if dt.tzinfo is None:
        dt = dt.astimezone()

    return dt.isoformat()


def get_busy_times(
    calendar_service,
    start_dt: datetime,
    end_dt: datetime,
    calendar_id: str = "primary",
) -> List[dict]:
    """
    Returns a list of busy windows between start_dt and end_dt.

    Example return:
    [
        {"start": "2026-04-17T10:00:00-04:00", "end": "2026-04-17T10:30:00-04:00"},
        {"start": "2026-04-17T13:00:00-04:00", "end": "2026-04-17T14:00:00-04:00"},
    ]
    """
    body = {
        "timeMin": to_google_datetime(start_dt),
        "timeMax": to_google_datetime(end_dt),
        "items": [{"id": calendar_id}],
    }

    result = calendar_service.freebusy().query(body=body).execute()
    return result["calendars"][calendar_id].get("busy", [])


def is_time_available(
    calendar_service,
    start_dt: datetime,
    end_dt: datetime,
    calendar_id: str = "primary",
) -> bool:
    """
    Returns True if the proposed time slot is free.
    Returns False if anything overlaps it.
    """
    busy_times = get_busy_times(
        calendar_service=calendar_service,
        start_dt=start_dt,
        end_dt=end_dt,
        calendar_id=calendar_id,
    )
    return len(busy_times) == 0


def create_appointment(
    calendar_service,
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
    location: str = "",
    attendee_emails: List[str] | None = None,
    calendar_id: str = "primary",
) -> dict:
    """
    Creates a calendar appointment and returns the created event dict.
    """
    if end_dt <= start_dt:
        raise ValueError("end_dt must be after start_dt")

    attendee_emails = attendee_emails or []

    event_body = {
        "summary": title,
        "description": description,
        "location": location,
        "start": {
            "dateTime": to_google_datetime(start_dt),
        },
        "end": {
            "dateTime": to_google_datetime(end_dt),
        },
        "attendees": [{"email": email} for email in attendee_emails],
    }

    created_event = (
        calendar_service.events()
        .insert(
            calendarId=calendar_id,
            body=event_body,
            sendUpdates="all",
        )
        .execute()
    )

    return created_event


def check_and_create_appointment(
    calendar_service,
    title: str,
    start_dt: datetime,
    end_dt: datetime,
    description: str = "",
    location: str = "",
    attendee_emails: List[str] | None = None,
    calendar_id: str = "primary",
) -> dict | None:
    """
    Checks if a time is available.
    If yes, creates the appointment.
    If not, returns None.
    """
    if not is_time_available(calendar_service, start_dt, end_dt, calendar_id):
        return None

    return create_appointment(
        calendar_service=calendar_service,
        title=title,
        start_dt=start_dt,
        end_dt=end_dt,
        description=description,
        location=location,
        attendee_emails=attendee_emails,
        calendar_id=calendar_id,
    )
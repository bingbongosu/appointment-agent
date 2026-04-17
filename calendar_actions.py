from datetime import datetime
from typing import List


def to_google_datetime(dt: datetime) -> str:
    """
    Converts a Python datetime into a Google-friendly ISO string.
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
    Returns the busy windows for a given time range.
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
    Returns True if the time slot is free.
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
    Creates a calendar event and returns the created event dictionary.
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
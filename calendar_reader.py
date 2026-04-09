from datetime import datetime, timedelta, timezone


def get_upcoming_events(calendar_service, days_ahead: int = 7) -> list[dict]:
    """
    Returns upcoming calendar events over the next N days.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)

    events_result = calendar_service.events().list(
        calendarId="primary",
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events_result.get("items", [])
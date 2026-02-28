"""
Google Calendar AI Tools - Single Script
All calendar operations as callable functions for an AI agent.
"""

import os
import pickle
import config
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ─── CONFIG ──────────────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = config.TIMEZONE
WORK_START = 9
WORK_END = 17

# ─── AUTH ────────────────────────────────────────────────────────────────────
_service = None


def _get_service():
    """Lazy-load and cache the calendar service."""
    global _service
    if _service:
        return _service

    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)

    _service = build("calendar", "v3", credentials=creds)
    return _service


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _parse_dt(raw: str) -> datetime:
    """Parse a dateTime or date string from the API."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _format_event(event: dict) -> dict:
    """Flatten an API event into a clean dict."""
    start_raw = event["start"].get("dateTime", event["start"].get("date", ""))
    end_raw = event["end"].get("dateTime", event["end"].get("date", ""))
    is_allday = "T" not in start_raw

    out = {
        "id": event["id"],
        "title": event.get("summary", "(No title)"),
        "start": start_raw,
        "end": end_raw,
        "all_day": is_allday,
        "location": event.get("location", ""),
        "description": event.get("description", ""),
        "meet_link": event.get("hangoutLink", ""),
        "status": event.get("status", ""),
        "calendar": event.get("_cal", "primary"),
        "attendees": [
            a["email"] for a in event.get("attendees", [])
        ],
        "html_link": event.get("htmlLink", ""),
    }

    if not is_allday:
        s, e = _parse_dt(start_raw), _parse_dt(end_raw)
        out["duration_min"] = int((e - s).total_seconds() / 60)
        out["time_display"] = f"{s.strftime('%I:%M %p')} – {e.strftime('%I:%M %p')}"
    else:
        out["duration_min"] = None
        out["time_display"] = "All Day"

    return out


def _dt_iso(dt: datetime) -> str:
    return dt.isoformat()


def _utc_iso(dt: datetime) -> str:
    return dt.isoformat() + "Z"


# ─── TOOL 1: GET EVENTS ─────────────────────────────────────────────────────

def get_events(
    start_date: str = None,
    end_date: str = None,
    days: int = 7,
    max_results: int = 50,
    calendar_id: str = "primary",
) -> list[dict]:
    """
    Get events in a date range.

    Args:
        start_date: ISO date string (default: now)
        end_date:   ISO date string (default: start + days)
        days:       fallback range if end_date not given
        max_results: max events to return
        calendar_id: which calendar

    Returns: list of event dicts
    """
    svc = _get_service()
    start = datetime.fromisoformat(start_date) if start_date else datetime.utcnow()
    end = datetime.fromisoformat(end_date) if end_date else start + timedelta(days=days)

    result = svc.events().list(
        calendarId=calendar_id,
        timeMin=_utc_iso(start),
        timeMax=_utc_iso(end),
        maxResults=max_results,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return [_format_event(e) for e in result.get("items", [])]


# ─── TOOL 2: GET TODAY / THIS WEEK ──────────────────────────────────────────

def get_todays_events() -> list[dict]:
    """Get all events for today."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return get_events(start_date=_dt_iso(today), days=1)


def get_this_weeks_events() -> list[dict]:
    """Get all events for the current week (Mon–Sun)."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return get_events(start_date=_dt_iso(monday), days=7)


# ─── TOOL 3: SEARCH EVENTS ──────────────────────────────────────────────────

def search_events(query: str, days: int = 30) -> list[dict]:
    """
    Full-text search across event titles, descriptions, locations.

    Args:
        query: search text
        days:  how far ahead to look

    Returns: matching events
    """
    svc = _get_service()
    now = datetime.utcnow()

    result = svc.events().list(
        calendarId="primary",
        timeMin=_utc_iso(now),
        timeMax=_utc_iso(now + timedelta(days=days)),
        q=query,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    return [_format_event(e) for e in result.get("items", [])]


# ─── TOOL 4: CREATE EVENT ───────────────────────────────────────────────────

def create_event(
    title: str,
    start: str,
    end: str = None,
    duration_min: int = 60,
    description: str = "",
    location: str = "",
    attendees: list[str] = None,
    all_day: bool = False,
    recurrence: str = None,
    add_meet: bool = False,
    reminder_minutes: list[int] = None,
    color_id: str = None,
) -> dict:
    """
    Create a calendar event.

    Args:
        title:        event name
        start:        ISO datetime or date string
        end:          ISO datetime or date (auto-calculated from duration if omitted)
        duration_min: used if end is omitted (default 60)
        description:  event body
        location:     address or room name
        attendees:    list of email addresses
        all_day:      if True, start/end are dates like "2025-07-15"
        recurrence:   RRULE string e.g. "RRULE:FREQ=WEEKLY;COUNT=10;BYDAY=MO"
        add_meet:     auto-create a Google Meet link
        reminder_minutes: list of reminder times e.g. [30, 1440]
        color_id:     Google Calendar color ID (1-11)

    Returns: created event dict
    """
    svc = _get_service()

    if all_day:
        event_body = {
            "start": {"date": start},
            "end": {"date": end or start},
        }
    else:
        start_dt = datetime.fromisoformat(start)
        if end:
            end_str = end
        else:
            end_str = _dt_iso(start_dt + timedelta(minutes=duration_min))

        event_body = {
            "start": {"dateTime": start, "timeZone": TIMEZONE},
            "end": {"dateTime": end_str, "timeZone": TIMEZONE},
        }

    event_body["summary"] = title
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location
    if attendees:
        event_body["attendees"] = [{"email": e} for e in attendees]
    if recurrence:
        event_body["recurrence"] = [recurrence]
    if color_id:
        event_body["colorId"] = color_id
    if reminder_minutes:
        event_body["reminders"] = {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": m} for m in reminder_minutes],
        }
    if add_meet:
        event_body["conferenceData"] = {
            "createRequest": {
                "requestId": f"ai-{datetime.now().timestamp()}",
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        }

    created = svc.events().insert(
        calendarId="primary",
        body=event_body,
        conferenceDataVersion=1 if add_meet else 0,
        sendUpdates="all" if attendees else "none",
    ).execute()

    return _format_event(created)


# ─── TOOL 5: QUICK ADD (NATURAL LANGUAGE) ───────────────────────────────────

def quick_add(text: str) -> dict:
    """
    Create event from natural language like Google's Quick Add.
    e.g. "Lunch with Sarah tomorrow at noon at Olive Garden"

    Args:
        text: natural language event description

    Returns: created event dict
    """
    svc = _get_service()
    created = svc.events().quickAdd(calendarId="primary", text=text).execute()
    return _format_event(created)


# ─── TOOL 6: UPDATE EVENT ───────────────────────────────────────────────────

def update_event(
    event_id: str,
    title: str = None,
    start: str = None,
    end: str = None,
    description: str = None,
    location: str = None,
    color_id: str = None,
    add_attendees: list[str] = None,
) -> dict:
    """
    Update fields on an existing event. Only provided fields are changed.

    Args:
        event_id:       the event to update
        title:          new title
        start:          new start dateTime
        end:            new end dateTime
        description:    new description
        location:       new location
        color_id:       new color (1-11)
        add_attendees:  emails to add (keeps existing)

    Returns: updated event dict
    """
    svc = _get_service()
    event = svc.events().get(calendarId="primary", eventId=event_id).execute()

    if title is not None:
        event["summary"] = title
    if start is not None:
        event["start"] = {"dateTime": start, "timeZone": TIMEZONE}
    if end is not None:
        event["end"] = {"dateTime": end, "timeZone": TIMEZONE}
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location
    if color_id is not None:
        event["colorId"] = color_id
    if add_attendees:
        existing = event.get("attendees", [])
        existing_emails = {a["email"] for a in existing}
        for email in add_attendees:
            if email not in existing_emails:
                existing.append({"email": email})
        event["attendees"] = existing

    updated = svc.events().update(
        calendarId="primary", eventId=event_id, body=event, sendUpdates="all"
    ).execute()

    return _format_event(updated)


# ─── TOOL 7: DELETE EVENT ───────────────────────────────────────────────────

def delete_event(event_id: str) -> dict:
    """
    Delete an event by ID.

    Args:
        event_id: the event to delete

    Returns: confirmation dict
    """
    svc = _get_service()
    svc.events().delete(calendarId="primary", eventId=event_id).execute()
    return {"deleted": True, "event_id": event_id}


# ─── TOOL 8: FIND FREE SLOTS ────────────────────────────────────────────────

def find_free_slots(
    date: str = None,
    duration_min: int = 30,
    attendees: list[str] = None,
) -> list[dict]:
    """
    Find available time slots on a given day.

    Args:
        date:         ISO date like "2025-07-15" (default: today)
        duration_min: minimum slot length in minutes
        attendees:    also check these people's availability

    Returns: list of {start, end, duration_min}
    """
    svc = _get_service()
    target = datetime.fromisoformat(date) if date else datetime.now()
    day_start = target.replace(hour=WORK_START, minute=0, second=0, microsecond=0)
    day_end = target.replace(hour=WORK_END, minute=0, second=0, microsecond=0)

    items = [{"id": "primary"}]
    if attendees:
        items.extend({"id": e} for e in attendees)

    fb = svc.freebusy().query(body={
        "timeMin": _utc_iso(day_start),
        "timeMax": _utc_iso(day_end),
        "items": items,
    }).execute()

    # merge all busy periods
    busy = []
    for cal_data in fb["calendars"].values():
        for slot in cal_data.get("busy", []):
            s = _parse_dt(slot["start"]).replace(tzinfo=None)
            e = _parse_dt(slot["end"]).replace(tzinfo=None)
            busy.append((s, e))
    busy.sort()

    merged = []
    for s, e in busy:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    # find gaps
    slots = []
    current = day_start
    for bs, be in merged:
        gap = int((bs - current).total_seconds() / 60)
        if gap >= duration_min:
            slots.append({
                "start": _dt_iso(current),
                "end": _dt_iso(bs),
                "duration_min": gap,
            })
        current = max(current, be)

    gap = int((day_end - current).total_seconds() / 60)
    if gap >= duration_min:
        slots.append({
            "start": _dt_iso(current),
            "end": _dt_iso(day_end),
            "duration_min": gap,
        })

    return slots


# ─── TOOL 9: AUTO-SCHEDULE ──────────────────────────────────────────────────

def auto_schedule(
    title: str,
    duration_min: int = 60,
    attendees: list[str] = None,
    description: str = "",
    earliest: str = None,
    search_days: int = 5,
) -> dict:
    """
    Automatically find the next free slot and book a meeting.

    Args:
        title:        meeting name
        duration_min: how long
        attendees:    emails to include
        description:  event body
        earliest:     ISO datetime, don't schedule before this
        search_days:  how many business days to search

    Returns: created event dict or error
    """
    start_dt = datetime.fromisoformat(earliest) if earliest else datetime.now() + timedelta(hours=1)

    for offset in range(search_days * 2):  # extra range to skip weekends
        check = start_dt + timedelta(days=offset)
        if check.weekday() >= 5:
            continue

        date_str = check.strftime("%Y-%m-%d")
        slots = find_free_slots(date=date_str, duration_min=duration_min, attendees=attendees)

        for slot in slots:
            slot_start = datetime.fromisoformat(slot["start"])
            if slot_start < start_dt and offset == 0:
                # on the first day, skip slots before earliest
                slot_start = start_dt.replace(
                    minute=(start_dt.minute // 15 + 1) * 15 % 60, second=0, microsecond=0
                )
                if int((datetime.fromisoformat(slot["end"]) - slot_start).total_seconds() / 60) < duration_min:
                    continue

            return create_event(
                title=title,
                start=_dt_iso(slot_start),
                duration_min=duration_min,
                attendees=attendees,
                description=description,
                add_meet=True,
            )

    return {"error": f"No {duration_min}min slot found in the next {search_days} business days"}


# ─── TOOL 10: LIST CALENDARS ────────────────────────────────────────────────

def list_calendars() -> list[dict]:
    """
    List all calendars the user can access.

    Returns: list of {id, name, access_role, primary, color}
    """
    svc = _get_service()
    cals = svc.calendarList().list().execute().get("items", [])
    return [
        {
            "id": c["id"],
            "name": c["summary"],
            "access_role": c.get("accessRole", ""),
            "primary": c.get("primary", False),
            "color": c.get("backgroundColor", ""),
        }
        for c in cals
    ]


# ─── TOOL 11: DAILY SUMMARY ─────────────────────────────────────────────────

def daily_summary(date: str = None) -> dict:
    """
    Generate a summary/report for a given day.

    Args:
        date: ISO date (default: today)

    Returns: {date, event_count, total_meeting_min, free_min, events}
    """
    target = datetime.fromisoformat(date) if date else datetime.now()
    day_str = target.strftime("%Y-%m-%d")
    day_start = target.replace(hour=0, minute=0, second=0, microsecond=0)

    events = get_events(start_date=_dt_iso(day_start), days=1)
    total_min = sum(e["duration_min"] or 0 for e in events)
    work_min = (WORK_END - WORK_START) * 60

    return {
        "date": day_str,
        "day_name": target.strftime("%A"),
        "event_count": len(events),
        "total_meeting_min": total_min,
        "free_min": max(0, work_min - total_min),
        "busiest_block": max(events, key=lambda e: e["duration_min"] or 0)["title"] if events else None,
        "events": events,
    }


# ─── TOOL REGISTRY (for AI frameworks) ──────────────────────────────────────

TOOLS = {
    "get_events": get_events,
    "get_todays_events": get_todays_events,
    "get_this_weeks_events": get_this_weeks_events,
    "search_events": search_events,
    "create_event": create_event,
    "quick_add": quick_add,
    "update_event": update_event,
    "delete_event": delete_event,
    "find_free_slots": find_free_slots,
    "auto_schedule": auto_schedule,
    "list_calendars": list_calendars,
    "daily_summary": daily_summary,
}


def run_tool(name: str, **kwargs):
    """Generic dispatcher — call any tool by name with kwargs."""
    if name not in TOOLS:
        return {"error": f"Unknown tool '{name}'. Available: {list(TOOLS.keys())}"}
    try:
        return TOOLS[name](**kwargs)
    except Exception as e:
        return {"error": str(e)}


# ─── DEMO / CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    def pp(data):
        print(json.dumps(data, indent=2, default=str))

    print("\n── Today's Events ──")
    pp(run_tool("get_todays_events"))

    print("\n── This Week ──")
    pp(run_tool("get_this_weeks_events"))

    print("\n── Free Slots Today ──")
    pp(run_tool("find_free_slots", duration_min=30))

    print("\n── Daily Summary ──")
    pp(run_tool("daily_summary"))

    print("\n── All Calendars ──")
    pp(run_tool("list_calendars"))

    # Uncomment to test write operations:
    # pp(run_tool("quick_add", text="Coffee with Alex Friday 2pm"))
    # pp(run_tool("create_event", title="Test", start="2025-07-15T10:00:00", duration_min=30))
    # pp(run_tool("search_events", query="standup"))
    # pp(run_tool("auto_schedule", title="1:1 Sync", duration_min=30))
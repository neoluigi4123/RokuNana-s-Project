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
            flow = InstalledAppFlow.from_client_secrets_file(
                "local_data/credentials.json", SCOPES
            )
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
        "attendees": [a["email"] for a in event.get("attendees", [])],
        "html_link": event.get("htmlLink", ""),
    }

    if not is_allday:
        s, e = _parse_dt(start_raw), _parse_dt(end_raw)
        out["duration_min"] = int((e - s).total_seconds() / 60)
        out["time_display"] = (
            f"{s.strftime('%I:%M %p')} – {e.strftime('%I:%M %p')}"
        )
    else:
        out["duration_min"] = None
        out["time_display"] = "All Day"

    return out


def _dt_iso(dt: datetime) -> str:
    return dt.isoformat()


def _utc_iso(dt: datetime) -> str:
    return dt.isoformat() + "Z"


def _resolve_date(date: str = None) -> datetime: # type: ignore
    """
    Resolve a date string (YYYY-MM-DD, 'today', 'tomorrow') into a datetime
    at midnight. Defaults to today if None.
    """
    if date is None:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    lower = date.strip().lower()
    now = datetime.now()

    if lower == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif lower == "tomorrow":
        return (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        return datetime.fromisoformat(date).replace(
            hour=0, minute=0, second=0, microsecond=0
        )


# ─── TOOL: GET EVENT ────────────────────────────────────────────────────────


def get_event(date: str = None) -> list[dict]: # type: ignore
    """
    Get events for a given date.

    Args:
        date: Date string (YYYY-MM-DD), 'today', 'tomorrow', or None for today.

    Returns: list of event dicts for that day.
    """
    svc = _get_service()
    day_start = _resolve_date(date)
    day_end = day_start + timedelta(days=1)

    result = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=_utc_iso(day_start),
            timeMax=_utc_iso(day_end),
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return [_format_event(e) for e in result.get("items", [])]


# ─── TOOL: SEARCH EVENT ─────────────────────────────────────────────────────


def search_event(query: str, days: int = 30) -> list[dict]:
    """
    Full-text search across event titles, descriptions, locations.

    Args:
        query: search text
        days:  how far ahead to look (default 30)

    Returns: matching events
    """
    svc = _get_service()
    now = datetime.utcnow()

    result = (
        svc.events()
        .list(
            calendarId="primary",
            timeMin=_utc_iso(now),
            timeMax=_utc_iso(now + timedelta(days=days)),
            q=query,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return [_format_event(e) for e in result.get("items", [])]


# ─── TOOL: CREATE EVENT ─────────────────────────────────────────────────────


def create_event(
    title: str,
    date: str,
    time: str = None, # type: ignore
) -> dict:
    """
    Create a calendar event.

    Args:
        title: Title / name of the event.
        date:  Date of the event (YYYY-MM-DD). Also accepts 'today' / 'tomorrow'.
        time:  Time of the event (HH:MM, 24-hour). If None, creates an all-day event.

    Returns: created event dict
    """
    svc = _get_service()
    day = _resolve_date(date)

    if time is None:
        # All-day event
        date_str = day.strftime("%Y-%m-%d")
        event_body = {
            "summary": title,
            "start": {"date": date_str},
            "end": {"date": date_str},
        }
    else:
        # Timed event — default 60 min duration
        parts = time.strip().split(":")
        hour, minute = int(parts[0]), int(parts[1])
        start_dt = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        end_dt = start_dt + timedelta(minutes=60)

        event_body = {
            "summary": title,
            "start": {"dateTime": _dt_iso(start_dt), "timeZone": TIMEZONE},
            "end": {"dateTime": _dt_iso(end_dt), "timeZone": TIMEZONE},
        }

    created = (
        svc.events()
        .insert(
            calendarId="primary",
            body=event_body,
            conferenceDataVersion=0,
            sendUpdates="none",
        )
        .execute()
    )

    return _format_event(created)


# ─── TOOL: UPDATE EVENT ─────────────────────────────────────────────────────


def update_event(
    event_id: str,
    title: str = None, # type: ignore
    date: str = None, # type: ignore
    time: str = None, # type: ignore
) -> dict:
    """
    Update fields on an existing event. Only provided fields are changed.

    Args:
        event_id: The event to update.
        title:    New title.
        date:     New date (YYYY-MM-DD). Also accepts 'today' / 'tomorrow'.
        time:     New time (HH:MM, 24-hour).

    Returns: updated event dict
    """
    svc = _get_service()
    event = svc.events().get(calendarId="primary", eventId=event_id).execute()

    if title is not None:
        event["summary"] = title

    # If date or time is provided, rebuild start/end
    if date is not None or time is not None:
        # Resolve the base date
        if date is not None:
            new_day = _resolve_date(date)
        else:
            # Keep existing date
            existing_start = event["start"].get(
                "dateTime", event["start"].get("date", "")
            )
            new_day = _parse_dt(existing_start).replace(tzinfo=None)
            new_day = new_day.replace(hour=0, minute=0, second=0, microsecond=0)

        if time is not None:
            parts = time.strip().split(":")
            hour, minute = int(parts[0]), int(parts[1])
            start_dt = new_day.replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )

            # Preserve original duration if possible
            old_start_raw = event["start"].get("dateTime")
            old_end_raw = event["end"].get("dateTime")
            if old_start_raw and old_end_raw:
                old_s = _parse_dt(old_start_raw).replace(tzinfo=None)
                old_e = _parse_dt(old_end_raw).replace(tzinfo=None)
                duration = old_e - old_s
            else:
                duration = timedelta(minutes=60)

            end_dt = start_dt + duration

            event["start"] = {"dateTime": _dt_iso(start_dt), "timeZone": TIMEZONE}
            event["end"] = {"dateTime": _dt_iso(end_dt), "timeZone": TIMEZONE}
        else:
            # Date changed but no time — keep existing time if timed, else all-day
            old_start_raw = event["start"].get("dateTime")
            if old_start_raw:
                old_s = _parse_dt(old_start_raw).replace(tzinfo=None)
                old_e = _parse_dt(
                    event["end"].get("dateTime", old_start_raw)
                ).replace(tzinfo=None)
                duration = old_e - old_s

                start_dt = new_day.replace(
                    hour=old_s.hour,
                    minute=old_s.minute,
                    second=0,
                    microsecond=0,
                )
                end_dt = start_dt + duration

                event["start"] = {
                    "dateTime": _dt_iso(start_dt),
                    "timeZone": TIMEZONE,
                }
                event["end"] = {
                    "dateTime": _dt_iso(end_dt),
                    "timeZone": TIMEZONE,
                }
            else:
                date_str = new_day.strftime("%Y-%m-%d")
                event["start"] = {"date": date_str}
                event["end"] = {"date": date_str}

    updated = (
        svc.events()
        .update(
            calendarId="primary",
            eventId=event_id,
            body=event,
            sendUpdates="all",
        )
        .execute()
    )

    return _format_event(updated)


# ─── TOOL: DELETE EVENT ──────────────────────────────────────────────────────


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


# ─── TOOL: FIND FREE SLOT ───────────────────────────────────────────────────


def find_free_slot(
    date: str,
    duration: int,
) -> list[dict]:
    """
    Find available time slots on a given day.

    Args:
        date:     Date to find free slots (YYYY-MM-DD).
        duration: Minimum slot length in minutes.

    Returns: list of {start, end, duration_min}
    """
    svc = _get_service()
    target = _resolve_date(date)
    day_start = target.replace(hour=WORK_START, minute=0, second=0, microsecond=0)
    day_end = target.replace(hour=WORK_END, minute=0, second=0, microsecond=0)

    items = [{"id": "primary"}]

    fb = (
        svc.freebusy()
        .query(
            body={
                "timeMin": _utc_iso(day_start),
                "timeMax": _utc_iso(day_end),
                "items": items,
            }
        )
        .execute()
    )

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
        if gap >= duration:
            slots.append(
                {
                    "start": _dt_iso(current),
                    "end": _dt_iso(bs),
                    "duration_min": gap,
                }
            )
        current = max(current, be)

    gap = int((day_end - current).total_seconds() / 60)
    if gap >= duration:
        slots.append(
            {
                "start": _dt_iso(current),
                "end": _dt_iso(day_end),
                "duration_min": gap,
            }
        )

    return slots


# ─── TOOL: DAILY SUMMARY ────────────────────────────────────────────────────


def daily_summary(date: str) -> dict:
    """
    Generate a summary/report for a given day.

    Args:
        date: Date for the summary (YYYY-MM-DD).

    Returns: {date, day_name, event_count, total_meeting_min, free_min, busiest_block, events}
    """
    target = _resolve_date(date)
    day_str = target.strftime("%Y-%m-%d")

    events = get_event(date=day_str)
    total_min = sum(e["duration_min"] or 0 for e in events)
    work_min = (WORK_END - WORK_START) * 60

    return {
        "date": day_str,
        "day_name": target.strftime("%A"),
        "event_count": len(events),
        "total_meeting_min": total_min,
        "free_min": max(0, work_min - total_min),
        "busiest_block": (
            max(events, key=lambda e: e["duration_min"] or 0)["title"]
            if events
            else None
        ),
        "events": events,
    }


# ─── DISPATCHER (for agent integration) ─────────────────────────────────────

TOOL_MAP = {
    "getEvent": lambda args: get_event(date=args.get("date")),
    "searchEvent": lambda args: search_event(query=args["query"]),
    "createEvent": lambda args: create_event(
        title=args["title"],
        date=args["date"],
        time=args.get("time"),
    ),
    "updateEvent": lambda args: update_event(
        event_id=args["event_id"],
        title=args.get("title"),
        date=args.get("date"),
        time=args.get("time"),
    ),
    "deleteEvent": lambda args: delete_event(event_id=args["event_id"]),
    "findFreeSlot": lambda args: find_free_slot(
        date=args["date"],
        duration=args["duration"],
    ),
    "dailySummary": lambda args: daily_summary(date=args["date"]),
}


def run_tool(tool_type: str, args: dict):
    """
    Dispatch a tool call by its schema type name.

    Args:
        tool_type: one of the keys in TOOL_MAP
        args:      dict of arguments matching the schema

    Returns: tool result (dict or list)
    """
    handler = TOOL_MAP.get(tool_type)
    if handler is None:
        return {"error": f"Unknown tool type: {tool_type}"}
    return handler(args)


# ─── DEMO / CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _get_service()  # trigger auth flow

    print("Today's events:")
    for e in get_event():
        print(f"  - {e['title']} at {e['time_display']}")

    print("\nSearch for 'lunch':")
    for e in search_event("lunch"):
        print(f"  - {e['title']} on {e['start'][:10]} at {e['time_display']}")

    print("\nCreating a test event...")
    new_event = create_event(
        title="Test Meeting",
        date="today",
        time="14:00",
    )
    print(
        f"  Created: {new_event['title']} at {new_event['time_display']}"
    )

    print("\nFree slots today (30 min):")
    today_str = datetime.now().strftime("%Y-%m-%d")
    for slot in find_free_slot(date=today_str, duration=30):
        print(f"  - {slot['start']} → {slot['end']} ({slot['duration_min']}min)")

    print("\nDaily summary:")
    summary = daily_summary(date=today_str)
    print(f"  {summary['day_name']}: {summary['event_count']} events, "
          f"{summary['free_min']}min free")
"""
Generate iCalendar (.ics) subscription files from parsed lunch menu data.

Produces one Calendar object per school level. Each lunch day becomes a
single all-day VEVENT. UIDs are stable ({date}-{level}@{domain}) so
calendar apps merge updates cleanly rather than creating duplicates.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from icalendar import Calendar, Event

DOMAIN = "curtlawson.dev"
CALENDAR_NAMES = {
    "elementary": "Elementary School Lunch",
    "middle": "Middle School Lunch",
    "high": "High School Lunch",
}


def _make_event(entry: dict, level: str, domain: str = DOMAIN) -> Event:
    lunch_date: date = entry["date"]
    items: list[str] = entry["items"]

    event = Event()
    event.add("uid", f"{lunch_date.strftime('%Y%m%d')}-{level}@{domain}")

    # All-day event: DTSTART is a date, DTEND is the next day
    event.add("dtstart", lunch_date)
    event.add("dtend", lunch_date + timedelta(days=1))

    # Use a deterministic DTSTAMP so the .ics file is content-stable
    event.add("dtstamp", datetime(lunch_date.year, lunch_date.month, lunch_date.day, tzinfo=timezone.utc))

    event.add("summary", items[0])
    event.add("description", "\n".join(f"• {item}" for item in items))

    return event


def build_calendar(menu: list[dict], level: str, domain: str = DOMAIN) -> Calendar:
    """
    Build an icalendar.Calendar from a parsed menu list.

    Args:
        menu:  List of {"date": date, "items": [str, ...]} from parse_menu().
        level: School level key used in UIDs and the calendar name
               ("elementary", "middle", or "high").

    Returns:
        An icalendar.Calendar ready for serialisation via .to_ical().
    """
    cal = Calendar()
    cal.add("prodid", f"-//lunch-bell//{level}//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "PUBLISH")
    cal.add("x-wr-calname", CALENDAR_NAMES.get(level, f"{level.title()} School Lunch"))
    cal.add("x-wr-caldesc", f"Daily lunch menu for {CALENDAR_NAMES.get(level, level)}")
    cal.add("x-wr-timezone", "America/Chicago")

    for entry in menu:
        cal.add_component(_make_event(entry, level, domain=domain))

    return cal


if __name__ == "__main__":
    import pathlib
    import sys
    from discover import discover_lunch_pdfs
    from parse import parse_menu
    import tempfile, requests

    output_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
    output_dir.mkdir(parents=True, exist_ok=True)

    pdfs = discover_lunch_pdfs()

    for level, url in sorted(pdfs.items()):
        print(f"Fetching {level} PDF...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(r.content)
            tmp_path = tmp.name

        menu = parse_menu(tmp_path)
        cal = build_calendar(menu, level)

        out_path = output_dir / f"{level}.ics"
        out_path.write_bytes(cal.to_ical())
        print(f"  Wrote {out_path} ({len(menu)} events)")

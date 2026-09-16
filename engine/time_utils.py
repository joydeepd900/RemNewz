"""
engine/time_utils.py — Timezone-aware time utilities for RemNewz.

Provides helpers for:
  - Getting "now" in the user's configured timezone.
  - Human-friendly formatting of datetimes.
  - Parsing deadline strings (used later by Remzy).
"""

import os
from datetime import datetime, timezone, timedelta
from dateutil import tz as dateutil_tz


def get_user_timezone():
    """Return a tzinfo object for the user's configured timezone.

    Reads TIMEZONE from env (IANA format, e.g. 'Asia/Kolkata').
    Falls back to UTC if not set or invalid.
    """
    tz_name = os.environ.get("TIMEZONE", "UTC")
    user_tz = dateutil_tz.gettz(tz_name)
    if user_tz is None:
        print(f"[time_utils] WARNING: Unknown timezone '{tz_name}', falling back to UTC.")
        return dateutil_tz.UTC
    return user_tz


def now_local():
    """Return the current datetime in the user's timezone."""
    return datetime.now(tz=get_user_timezone())


def format_datetime(dt, style="full"):
    """Format a datetime for display in Telegram messages.

    Args:
        dt: A datetime object (timezone-aware or naive).
        style: 'full'  → 'Mon, 15 Sep 2026 · 08:00 AM IST'
               'short' → '15 Sep, 08:00 AM'
               'time'  → '08:00 AM'
               'date'  → '15 Sep 2026'
               'relative' → 'in 3 hours' / '2 days ago'

    Returns:
        A formatted string.
    """
    user_tz = get_user_timezone()

    # If naive, assume it's in the user's timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=user_tz)
    else:
        dt = dt.astimezone(user_tz)

    if style == "full":
        return dt.strftime("%a, %d %b %Y · %I:%M %p %Z")
    elif style == "short":
        return dt.strftime("%d %b, %I:%M %p")
    elif style == "time":
        return dt.strftime("%I:%M %p")
    elif style == "date":
        return dt.strftime("%d %b %Y")
    elif style == "relative":
        return _relative_time(dt, user_tz)
    else:
        return dt.isoformat()


def _relative_time(dt, user_tz):
    """Compute a human-friendly relative time string."""
    now = datetime.now(tz=user_tz)
    diff = dt - now
    total_seconds = diff.total_seconds()
    abs_seconds = abs(total_seconds)

    if abs_seconds < 60:
        return "just now"
    elif abs_seconds < 3600:
        minutes = int(abs_seconds // 60)
        label = f"{minutes} min{'s' if minutes > 1 else ''}"
    elif abs_seconds < 86400:
        hours = int(abs_seconds // 3600)
        label = f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        days = int(abs_seconds // 86400)
        label = f"{days} day{'s' if days > 1 else ''}"

    return f"in {label}" if total_seconds > 0 else f"{label} ago"

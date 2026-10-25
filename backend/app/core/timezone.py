"""Timezone handling utilities for Scheduler.

Ensures explicit term time zone handling across academic calendar,
timetabling sessions, and examination seatings without scattered
implicit local conversions.
"""

from datetime import datetime, date, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def get_term_timezone(tz_name: str | None) -> ZoneInfo:
    """Resolve an IANA timezone string to a ZoneInfo instance.
    Defaults to UTC if None or invalid.
    """
    if not tz_name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def validate_timezone(tz_name: str) -> bool:
    """Validate whether a string is a recognized IANA timezone identifier."""
    try:
        ZoneInfo(tz_name)
        return True
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        return False


def to_utc(dt: datetime) -> datetime:
    """Normalize any datetime to UTC timezone-aware datetime."""
    if dt.tzinfo is None:
        # Naive datetime is treated as UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def from_utc_to_term(dt_utc: datetime, tz_name: str) -> datetime:
    """Convert a UTC datetime to the academic term local timezone."""
    term_tz = get_term_timezone(tz_name)
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return dt_utc.astimezone(term_tz)


def combine_term_datetime(target_date: date, target_time: time, tz_name: str) -> datetime:
    """Combine a calendar date and local period time in the term's timezone,
    returning a timezone-aware UTC datetime for uniform database persistence.
    """
    term_tz = get_term_timezone(tz_name)
    local_dt = datetime.combine(target_date, target_time, tzinfo=term_tz)
    return local_dt.astimezone(timezone.utc)
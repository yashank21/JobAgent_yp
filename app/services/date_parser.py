"""
Date parsing utilities.
"""

from datetime import datetime, timezone


def parse_greenhouse_date(value: str) -> datetime | None:
    """
    Parse a Greenhouse ISO-8601 timestamp and normalize to UTC.

    Returns a UTC timezone-aware datetime when valid.
    Returns None when the value is empty or invalid.
    """
    if not value:
        return None

    try:
        dt = datetime.fromisoformat(value)
        # Handle naive datetimes by assuming UTC
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        # Convert offset-aware datetimes to UTC
        return dt.astimezone(timezone.utc)

    except (ValueError, TypeError):
        return None
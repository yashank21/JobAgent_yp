"""
Date parsing utilities.
"""

from datetime import datetime


def parse_greenhouse_date(value: str) -> datetime | None:
    """
    Parse a Greenhouse ISO-8601 timestamp.

    Returns a timezone-aware datetime when valid.
    Returns None when the value is empty or invalid.
    """

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)

    except ValueError:
        return None
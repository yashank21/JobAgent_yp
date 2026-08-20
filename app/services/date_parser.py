"""
Date parsing utilities.
"""

import re
from datetime import datetime, timedelta, timezone


def parse_greenhouse_date(
    value: str,
) -> datetime | None:
    """
    Parse a Greenhouse ISO-8601 timestamp and normalize to UTC.

    Returns a UTC timezone-aware datetime when valid.
    Returns None when the value is empty or invalid.
    """

    if not value:
        return None

    try:

        dt = datetime.fromisoformat(value)

        # Handle naive datetimes by assuming UTC.
        if dt.tzinfo is None:
            return dt.replace(
                tzinfo=timezone.utc
            )

        # Convert offset-aware datetimes to UTC.
        return dt.astimezone(
            timezone.utc
        )

    except (
        ValueError,
        TypeError,
    ):

        return None


def parse_wellfound_date(
    value: str,
    reference_time: datetime | None = None,
) -> datetime | None:
    """
    Parse Wellfound relative posting dates.

    Examples:

        "Posted: just now"
            -> reference_time

        "Posted: 5 minutes ago"
            -> reference_time - 5 minutes

        "Posted: 3 hours ago"
            -> reference_time - 3 hours

        "Posted: 1 day ago"
            -> reference_time - 1 day

        "Posted: 2 weeks ago"
            -> reference_time - 14 days

        "Posted: 1 month ago"
            -> reference_time - 30 days

    Wellfound exposes relative dates rather than exact
    timestamps, so the resulting datetime is approximate.

    Returns:
        UTC timezone-aware datetime, or None if the
        value cannot be parsed.
    """

    if not value:
        return None

    # ---------------------------------------------------------
    # Reference time
    # ---------------------------------------------------------

    if reference_time is None:

        reference_time = datetime.now(
            timezone.utc
        )

    elif reference_time.tzinfo is None:

        reference_time = reference_time.replace(
            tzinfo=timezone.utc
        )

    else:

        reference_time = reference_time.astimezone(
            timezone.utc
        )

    # ---------------------------------------------------------
    # Normalize text
    # ---------------------------------------------------------

    text = value.strip().lower()

    # Examples:
    #
    # Posted: 2 weeks ago
    # 2 weeks ago
    # Posted: 2 weeks ago • Recruiter recently active
    #
    text = re.sub(
        r"^posted:\s*",
        "",
        text,
    )

    text = text.split(
        "•",
        1,
    )[0].strip()

    # ---------------------------------------------------------
    # Just now
    # ---------------------------------------------------------

    if text in {
        "just now",
        "now",
        "today",
    }:

        return reference_time

    # ---------------------------------------------------------
    # Numeric relative time
    # ---------------------------------------------------------

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\s*"
        r"(minute|minutes|hour|hours|"
        r"day|days|week|weeks|"
        r"month|months|year|years)"
        r"\s+ago\b",
        text,
        re.IGNORECASE,
    )

    if not match:
        return None

    amount = float(
        match.group(1)
    )

    unit = match.group(2).lower()

    # ---------------------------------------------------------
    # Convert relative time to timedelta.
    #
    # Months and years are deliberately approximated.
    # Wellfound does not provide the exact timestamp.
    # ---------------------------------------------------------

    if unit in {
        "minute",
        "minutes",
    }:

        delta = timedelta(
            minutes=amount
        )

    elif unit in {
        "hour",
        "hours",
    }:

        delta = timedelta(
            hours=amount
        )

    elif unit in {
        "day",
        "days",
    }:

        delta = timedelta(
            days=amount
        )

    elif unit in {
        "week",
        "weeks",
    }:

        delta = timedelta(
            weeks=amount
        )

    elif unit in {
        "month",
        "months",
    }:

        delta = timedelta(
            days=amount * 30
        )

    elif unit in {
        "year",
        "years",
    }:

        delta = timedelta(
            days=amount * 365
        )

    else:

        return None

    return reference_time - delta
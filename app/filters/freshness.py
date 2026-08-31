"""
Job freshness filtering utilities.

Determines whether a job was posted within the
configured freshness window.
"""

from datetime import datetime, timedelta, timezone

from app.models.job import Job


FRESHNESS_HOURS = 48


def is_recent_job(
    job: Job,
    hours: int = FRESHNESS_HOURS,
) -> bool:
    """
    Return True when a job was posted within the
    specified number of hours.

    Jobs without posted_at are rejected because
    freshness cannot be verified.
    """

    posted_at = job.posted_at

    if posted_at is None:
        return False

    now = datetime.now(timezone.utc)

    # Handle naive datetimes safely.
    if posted_at.tzinfo is None:
        posted_at = posted_at.replace(
            tzinfo=timezone.utc
        )

    age = now - posted_at

    return timedelta(0) <= age <= timedelta(
        hours=hours
    )

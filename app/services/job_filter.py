"""
Job filtering utilities.
"""

from datetime import datetime, timedelta, timezone

from app.models.job import Job


def filter_recent_jobs(
    jobs: list[Job],
    hours: int = 24,
) -> list[Job]:
    """
    Return jobs posted within the last `hours` hours.

    Jobs without a posted_at value are ignored.
    Future-dated jobs are also ignored.
    """

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=hours)

    recent_jobs = []

    for job in jobs:

        if job.posted_at is None:
            continue

        posted_at = job.posted_at

        # Normalize naive datetimes to UTC.
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(
                tzinfo=timezone.utc
            )

        if cutoff <= posted_at <= now:
            recent_jobs.append(job)

    return recent_jobs
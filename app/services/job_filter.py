from datetime import datetime, timezone, timedelta
from typing import List
from app.models.job import Job


def filter_recent_jobs(
    jobs: List[Job],
    hours: float = 24.0,
) -> List[Job]:

    now = datetime.now(timezone.utc)

    cutoff_time = now - timedelta(
    hours=hours,
)

    recent_jobs = []

    for job in jobs:

        posted_at = job.posted_at

        if posted_at is None:
            continue

        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(
                tzinfo=timezone.utc,
            )

        if cutoff_time <= posted_at <= now:
            recent_jobs.append(job)

    return recent_jobs
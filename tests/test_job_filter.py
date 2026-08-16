from datetime import datetime, timedelta, timezone

from app.models.job import Job
from app.services.job_filter import filter_recent_jobs


def make_job(
    job_id: str,
    posted_at: datetime | None,
) -> Job:

    return Job(
        id=job_id,
        title=f"Job {job_id}",
        company="Example Corp",
        posted_at=posted_at,
    )


def test_filter_recent_jobs():

    now = datetime.now(timezone.utc)

    jobs = [
        make_job(
            "recent",
            now - timedelta(hours=5),
        ),
        make_job(
            "old",
            now - timedelta(hours=30),
        ),
    ]

    result = filter_recent_jobs(jobs)

    assert len(result) == 1
    assert result[0].id == "recent"


def test_filter_jobs_without_posted_date():

    jobs = [
        make_job("unknown", None),
    ]

    result = filter_recent_jobs(jobs)

    assert result == []


def test_filter_future_jobs():

    now = datetime.now(timezone.utc)

    jobs = [
        make_job(
            "future",
            now + timedelta(hours=2),
        ),
    ]

    result = filter_recent_jobs(jobs)

    assert result == []


def test_custom_time_window():

    now = datetime.now(timezone.utc)

    jobs = [
        make_job(
            "recent",
            now - timedelta(hours=48),
        ),
        make_job(
            "old",
            now - timedelta(hours=72),
        ),
    ]

    result = filter_recent_jobs(
        jobs,
        hours=48,
    )

    assert len(result) == 1
    assert result[0].id == "recent"
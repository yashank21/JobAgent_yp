"""Job deduplication utilities."""

import re
from collections import Counter

from app.models.job import Job


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^a-z0-9 ]", "", value)

    return value


def _job_key(job: Job) -> tuple[str, str, str]:
    """
    Build a stable identity for a job.

    Application URL is preferred because it is the strongest
    identifier when available.
    """

    application_url = _normalize(
        getattr(job, "application_url", "")
    )

    if application_url:
        return ("url", application_url, "")

    return (
        _normalize(getattr(job, "company", "")),
        _normalize(getattr(job, "title", "")),
        _normalize(getattr(job, "location", "")),
    )


def deduplicate_jobs(
    jobs: list[Job],
) -> list[Job]:
    """
    Remove duplicate job postings while preserving order.
    """

    seen: set[tuple[str, str, str]] = set()
    unique_jobs: list[Job] = []

    for job in jobs:
        key = _job_key(job)

        if key in seen:
            continue

        seen.add(key)
        unique_jobs.append(job)

    removed = len(jobs) - len(unique_jobs)

    print(
        f"Deduplication: "
        f"{len(jobs):,} → {len(unique_jobs):,} jobs "
        f"({removed:,} duplicates removed)"
    )

    return unique_jobs
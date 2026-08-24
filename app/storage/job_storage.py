"""
Job dataset persistence utilities.

Stores and loads normalized Job objects as JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from app.models.job import Job


DEFAULT_DATASET_PATH = Path(
    "data/wellfound_jobs.json"
)


def save_jobs(
    jobs: list[Job],
    path: Path = DEFAULT_DATASET_PATH,
) -> None:
    """
    Save normalized jobs to JSON.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = []

    for job in jobs:
        item = asdict(job)

        if job.posted_at is not None:
            item["posted_at"] = (
                job.posted_at.isoformat()
            )

        if job.fetched_at is not None:
            item["fetched_at"] = (
                job.fetched_at.isoformat()
            )

        data.append(item)

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


def load_jobs(
    path: Path = DEFAULT_DATASET_PATH,
) -> list[Job]:
    """
    Load normalized jobs from JSON.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    jobs = []

    for item in data:

        posted_at = item.get(
            "posted_at"
        )

        fetched_at = item.get(
            "fetched_at"
        )

        if posted_at:
            posted_at = datetime.fromisoformat(
                posted_at
            )

        if fetched_at:
            fetched_at = datetime.fromisoformat(
                fetched_at
            )

        item["posted_at"] = posted_at
        item["fetched_at"] = fetched_at

        jobs.append(
            Job(**item)
        )

    return jobs
"""
Job ranking utilities.

Ranks jobs for a candidate using their overall match score.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.job_scorer import calculate_job_score


def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
    limit: int | None = None,
) -> list[tuple[Job, float]]:
    """
    Rank jobs from highest to lowest candidate match score.
    """

    scored_jobs = [
        (
            job,
            calculate_job_score(
                candidate,
                job,
            ),
        )
        for job in jobs
    ]

    scored_jobs.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    if limit is not None:
        return scored_jobs[:limit]

    return scored_jobs
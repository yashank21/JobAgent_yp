"""
Job ranking utilities.

Ranks only eligible jobs for a candidate using their
overall match score.
"""

from app.eligibility.eligibility import check_eligibility
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.job_scorer import calculate_job_score


def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
    limit: int | None = None,
) -> list[tuple[Job, float]]:
    """
    Rank eligible jobs from highest to lowest candidate match score.

    Eligibility is a hard gate:
    an ineligible job must never be scored or ranked.
    """

    eligible_jobs: list[Job] = []

    for job in jobs:

        eligibility = check_eligibility(
            candidate,
            job,
        )

        if eligibility.eligible:
            eligible_jobs.append(job)

    scored_jobs = [
        (
            job,
            calculate_job_score(
                candidate,
                job,
            ),
        )
        for job in eligible_jobs
    ]

    scored_jobs.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    if limit is not None:
        return scored_jobs[:limit]

    return scored_jobs
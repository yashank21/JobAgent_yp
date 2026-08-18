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
) -> list[tuple[Job, float, list[str]]]:
    """
    Rank eligible jobs from highest to lowest candidate match score.

    Eligibility is a hard gate:
    an ineligible job must never be scored or ranked.
    """
    scored_jobs = []

    for job in jobs:
        # 1. Hard Gate: Eligibility Check
        eligibility = check_eligibility(candidate, job)
        if not eligibility.eligible:
            continue  # REJECT IMMEDIATELY — do not score

        # 2. Score only eligible jobs
        score = calculate_job_score(candidate, job)
        scored_jobs.append((job, score, eligibility.reasons))

    # Sort descending by match score
    scored_jobs.sort(key=lambda item: item[1], reverse=True)

    if limit is not None:
        return scored_jobs[:limit]

    return scored_jobs
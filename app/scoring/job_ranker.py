"""
Job ranking utilities.

Compatibility wrapper around the V2 scoring engine.

The authoritative ranking implementation lives in
app.scoring.final_scorer.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.final_scorer import rank_jobs as rank_jobs_v2


def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
    limit: int | None = None,
):
    """
    Rank jobs using the V2 scoring engine.

    V2 performs:
        1. Hard eligibility filtering
        2. Skill scoring
        3. Role scoring
        4. Experience scoring
        5. Location scoring
        6. Mismatch caps
        7. Final ranking
    """

    ranked_jobs = rank_jobs_v2(
        candidate,
        jobs,
    )

    if limit is not None:
        return ranked_jobs[:limit]

    return ranked_jobs
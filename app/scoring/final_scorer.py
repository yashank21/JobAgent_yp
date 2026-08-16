"""
Final job scoring utilities.

Combines individual match dimensions into a single
final score for ranking jobs.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.match import JobMatch
from app.scoring.job_scorer import calculate_skill_score
from app.scoring.role_scorer import calculate_role_score
# from app.eligibility.eligibility import is_job_eligible
from app.eligibility.eligibility import (
    check_eligibility,
)


SKILL_WEIGHT = 0.50
ROLE_WEIGHT = 0.25
EXPERIENCE_WEIGHT = 0.15
LOCATION_WEIGHT = 0.10


def calculate_experience_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate experience compatibility from 0 to 100.

    No explicit requirement means we do not penalize the job.
    """

    required = job.experience_years_required

    if required is None or required <= 0:
        return 100.0

    if candidate.experience_years >= required:
        return 100.0

    if required == 0:
        return 100.0

    return min(
        100.0,
        (candidate.experience_years / required) * 100,
    )


def calculate_location_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate location compatibility from 0 to 100.
    """

    if not candidate.preferred_locations:
        return 100.0

    location = job.location.lower()

    remote = (
        "remote" in location
        or "remote" in job.remote_type.lower()
    )

    if remote:
        return 100.0

    for preferred in candidate.preferred_locations:
        if preferred.lower() in location:
            return 100.0

    return 0.0


def calculate_final_score(
    skill_score: float,
    role_score: float,
    experience_score: float,
    location_score: float,
) -> float:
    """
    Combine individual scores into a final score.
    """

    score = (
        skill_score * SKILL_WEIGHT
        + role_score * ROLE_WEIGHT
        + experience_score * EXPERIENCE_WEIGHT
        + location_score * LOCATION_WEIGHT
    )

    return round(score, 2)


def score_job(
    candidate: CandidateProfile,
    job: Job,
) -> JobMatch:
    """
    Produce a complete JobMatch for one job.
    """

    eligibility = check_eligibility(
    candidate,
    job,
)

    skill_score = calculate_skill_score(
        candidate,
        job,
    )

    role_score = calculate_role_score(
        candidate,
        job,
    )

    experience_score = calculate_experience_score(
        candidate,
        job,
    )

    location_score = calculate_location_score(
        candidate,
        job,
    )

    final_score = calculate_final_score(
        skill_score=skill_score,
        role_score=role_score,
        experience_score=experience_score,
        location_score=location_score,
    )

    return JobMatch(
    job=job,
    eligible=eligibility.eligible,
    skill_score=skill_score,
    role_score=role_score,
    experience_score=experience_score,
    location_score=location_score,
    final_score=final_score,
    eligibility_reasons=eligibility.reasons,
)


def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
) -> list[JobMatch]:
    """
    Score and rank jobs from highest to lowest.

    Ineligible jobs are excluded from the ranked results.
    """

    matches = [
        score_job(candidate, job)
        for job in jobs
    ]

    eligible_matches = [
        match
        for match in matches
        if match.eligible
    ]

    return sorted(
        eligible_matches,
        key=lambda match: match.final_score,
        reverse=True,
    )
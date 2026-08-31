"""
Final job ranking utilities.

Combines:
    - Skill compatibility
    - Role compatibility
    - Experience compatibility
    - Location compatibility

All scoring is candidate-driven and candidate-agnostic.
"""

from __future__ import annotations

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.match import JobMatch

from app.eligibility.eligibility import check_eligibility
from app.scoring.job_scorer import calculate_skill_score
from app.scoring.role_scorer import calculate_role_score
from app.scoring.experience_scorer import calculate_experience_score
from app.services.skill_normalizer import normalize_skills


# ============================================================
# WEIGHTS
# ============================================================

ROLE_WEIGHT = 0.30
SKILL_WEIGHT = 0.40
EXPERIENCE_WEIGHT = 0.20
LOCATION_WEIGHT = 0.10


# ============================================================
# LOCATION
# ============================================================

def calculate_location_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate candidate/job location compatibility.
    """

    if not candidate.preferred_locations:
        return 100.0

    from app.location.location_normalizer import location_matches

    matches = location_matches(
        job_location=getattr(
            job,
            "location",
            "",
        ),
        preferred_locations=candidate.preferred_locations,
        remote_type=getattr(
            job,
            "remote_type",
            "",
        ),
    )

    return 100.0 if matches else 0.0


# ============================================================
# HELPERS
# ============================================================

def _job_lists_skills(job: Job) -> bool:
    """
    Return True when the job contains usable skill information.
    """

    return bool(
        normalize_skills(
            getattr(
                job,
                "required_skills",
                [],
            )
            or []
        )
        or normalize_skills(
            getattr(
                job,
                "preferred_skills",
                [],
            )
            or []
        )
    )


# ============================================================
# FINAL SCORE
# ============================================================

def calculate_final_score(
    skill_score: float | None,
    role_score: float,
    experience_score: float,
    location_score: float,
) -> float:
    """
    Calculate the final candidate-job compatibility score.

    When skill information is unavailable, its weight is
    redistributed across the remaining scoring dimensions.
    """

    if skill_score is None:

        remaining_weight = (
            ROLE_WEIGHT
            + EXPERIENCE_WEIGHT
            + LOCATION_WEIGHT
        )

        score = (
            role_score
            * (ROLE_WEIGHT / remaining_weight)
            + experience_score
            * (EXPERIENCE_WEIGHT / remaining_weight)
            + location_score
            * (LOCATION_WEIGHT / remaining_weight)
        )

    else:

        score = (
            skill_score * SKILL_WEIGHT
            + role_score * ROLE_WEIGHT
            + experience_score * EXPERIENCE_WEIGHT
            + location_score * LOCATION_WEIGHT
        )

    return round(
        max(
            0.0,
            min(
                100.0,
                score,
            ),
        ),
        2,
    )


# ============================================================
# SCORE ONE JOB
# ============================================================

def score_job(
    candidate: CandidateProfile,
    job: Job,
) -> JobMatch:
    """
    Score one job against one candidate.
    """

    eligibility = check_eligibility(
        candidate,
        job,
    )

    listed_skills = _job_lists_skills(job)

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
        skill_score=(
            skill_score
            if listed_skills
            else None
        ),
        role_score=role_score,
        experience_score=experience_score,
        location_score=location_score,
    )

    return JobMatch(
        job=job,
        eligible=eligibility.eligible,
        skill_score=round(
            skill_score,
            2,
        ),
        role_score=round(
            role_score,
            2,
        ),
        experience_score=round(
            experience_score,
            2,
        ),
        location_score=round(
            location_score,
            2,
        ),
        final_score=final_score,
        eligibility_reasons=eligibility.reasons,
    )


# ============================================================
# RANK JOBS
# ============================================================

def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
) -> list[JobMatch]:
    """
    Score and rank eligible jobs from highest to lowest.
    """

    matches = [
        score_job(
            candidate,
            job,
        )
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
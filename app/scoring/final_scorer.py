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
from app.scoring.experience_scorer import (
    calculate_experience_score,
    classify_experience_risk,
)
from app.services.skill_normalizer import normalize_skills
from app.scoring.role_normalizer import RoleFamily, classify_role


# ============================================================
# WEIGHTS
# ============================================================

ROLE_WEIGHT = 0.30
SKILL_WEIGHT = 0.40
EXPERIENCE_WEIGHT = 0.20
LOCATION_WEIGHT = 0.10

# Confidence never penalizes more than that fraction.
MIN_CONFIDENCE = 0.70


# ============================================================
# LOCATION
# ============================================================

def calculate_location_score(
    candidate: CandidateProfile,
    job: Job,
) -> float | None:
    """
    Calculate candidate/job location compatibility.

    Returns None when the user has not configured a location
    preference (empty preferred_locations list).
    """

    if not candidate.preferences.preferred_locations:
        return None

    from app.location.location_normalizer import location_matches

    matches = location_matches(
        job_location=getattr(
            job,
            "location",
            "",
        ),
        preferred_locations=candidate.preferences.preferred_locations,
        remote_type=getattr(
            job,
            "remote_type",
            "",
        ),
    )

    return 100.0 if matches else 0.0


# ============================================================
# INFORMATION AVAILABILITY
# ============================================================

def _skill_information_available(job: Job) -> bool:
    """Return True if the job has usable skill information."""
    return bool(
        normalize_skills(getattr(job, "required_skills", []) or [])
        or normalize_skills(getattr(job, "preferred_skills", []) or [])
    )


def _role_information_available(job: Job) -> bool:
    """Return True if the job has a classifiable role family."""
    job_family = classify_role(getattr(job, "title", ""))
    return job_family != RoleFamily.UNKNOWN


def _experience_information_available(job: Job) -> bool:
    """Return True if experience information is available.

    Experience is always considered available because the scorer
    uses explicit numeric, parsed text, or seniority fallback.
    """
    return True


def _location_information_available(job: Job) -> bool:
    """Return True if the job has location information."""
    location = getattr(job, "location", "") or ""
    remote_type = getattr(job, "remote_type", "") or ""
    return bool(location.strip() or remote_type.strip())


def calculate_confidence(job: Job) -> float:
    """
    Calculate confidence in the compatibility calculation.

    Confidence is based on availability of ranking-relevant
    job information, NOT match quality.

    Returns a value between 0.0 and 1.0.
    """
    available_weight = 0.0

    if _skill_information_available(job):
        available_weight += SKILL_WEIGHT

    if _role_information_available(job):
        available_weight += ROLE_WEIGHT

    if _experience_information_available(job):
        available_weight += EXPERIENCE_WEIGHT

    if _location_information_available(job):
        available_weight += LOCATION_WEIGHT

    return available_weight


# ============================================================
# FINAL SCORE
# ============================================================

def calculate_final_score(
    skill_score: float | None,
    role_score: float | None,
    experience_score: float | None,
    location_score: float | None,
) -> float:
    """
    Calculate the compatibility score (weighted average of active
    dimensions).

    Formula:
        compatibility = sum(score_i * (weight_i / total_active_weight))

    Where:
        total_active_weight = sum(weight_i for dimensions where score_i is not None)
        Weights: skill=0.40, role=0.30, experience=0.20, location=0.10

    Semantic contract for each dimension:

        float (0-100) = actual compatibility score
            0.0   = known mismatch (hurts the score)
            50.0  = information unavailable / neutral (contributes 50)
            100.0 = known match (helps the score)

        None = candidate preference not configured
            (e.g., no preferred_roles, no preferred_locations)
            Excluded from scoring, weight redistributed proportionally.
    """

    dimensions = {
        SKILL_WEIGHT: skill_score,
        ROLE_WEIGHT: role_score,
        EXPERIENCE_WEIGHT: experience_score,
        LOCATION_WEIGHT: location_score,
    }

    active = {
        w: s
        for w, s in dimensions.items()
        if s is not None
    }

    if not active:
        return 0.0

    total_weight = sum(active.keys())

    score = sum(
        s * (w / total_weight)
        for w, s in active.items()
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


def calculate_ranking_score(
    compatibility: float,
    confidence: float,
) -> float:
    """
    Calculate the final ranking score from compatibility and confidence.

    Formula:
        ranking_score = compatibility * confidence_factor

    Where:
        confidence_factor = MIN_CONFIDENCE + (1 - MIN_CONFIDENCE) * confidence

    This ensures:
        - Maximum confidence (1.0) → factor = 1.0 (no penalty)
        - Zero confidence (0.0) → factor = 0.7 (30% penalty max)
        - Confidence never overwhelms genuine compatibility
    """

    confidence_factor = MIN_CONFIDENCE + (1.0 - MIN_CONFIDENCE) * confidence

    return round(
        max(
            0.0,
            min(
                100.0,
                compatibility * confidence_factor,
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

    # Experience risk: explainable warning, NOT a ranking penalty.
    # Risk does NOT modify compatibility_score or final_score.
    _req_years = getattr(
        job, "experience_years_required", None,
    )
    try:
        _req_float = float(_req_years) if _req_years is not None else None
    except (TypeError, ValueError):
        _req_float = None
    _cand_years = getattr(
        candidate.facts, "experience_years", 0.0,
    ) or 0.0
    _strictness = getattr(
        job, "requirement_strictness", "unknown",
    ) or "unknown"
    experience_risk = classify_experience_risk(
        _cand_years,
        _req_float,
        _strictness,
    )

    location_score = calculate_location_score(
        candidate,
        job,
    )

    # Compatibility: weighted average of active dimensions.
    compatibility = calculate_final_score(
        skill_score=skill_score,
        role_score=role_score,
        experience_score=experience_score,
        location_score=location_score,
    )

    # Confidence: based on job information availability.
    confidence = calculate_confidence(job)

    # Final ranking score: compatibility weighted by confidence.
    final_score = calculate_ranking_score(
        compatibility,
        confidence,
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
        ) if role_score is not None else None,
        experience_score=round(
            experience_score,
            2,
        ),
        experience_risk=experience_risk,
        location_score=round(
            location_score,
            2,
        ) if location_score is not None else None,
        compatibility_score=compatibility,
        confidence=round(confidence, 2),
        final_score=final_score,
        eligibility_reasons=eligibility.reasons,
    )


# ============================================================
# RANK JOBS
# ============================================================

def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
    limit: int | None = None,
) -> list[JobMatch]:
    """
    Score and rank eligible jobs from highest to lowest.

    If limit is provided, return only the top N eligible matches.
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

    # Rank eligible matches with deterministic tie-breaking.
    #
    # Priority order:
    #   1. ranking score (descending)
    #   2. confidence (descending)
    #   3. compatibility score (descending)
    #   4. job.id (ascending) — stable canonical identifier
    ranked_matches = sorted(
        eligible_matches,
        key=lambda match: (
            -match.final_score,
            -match.confidence,
            -match.compatibility_score,
            match.job.id,
        ),
    )

    if limit is not None:
        return ranked_matches[:limit]

    return ranked_matches
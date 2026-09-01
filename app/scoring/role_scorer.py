"""
Role compatibility scoring.

Candidate-driven and candidate-agnostic.

Scoring sources:
    1. Explicit preferred roles
    2. Secondary roles
    3. Resume-derived roles

RoleFamily is used only to determine whether two roles belong to
the same broad family. No candidate-specific compatibility matrix
is used.
"""

from __future__ import annotations

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_normalizer import RoleFamily, classify_role


# Explicit user intent is strongest.
PREFERRED_WEIGHT = 1.00
SECONDARY_WEIGHT = 0.85
RESUME_WEIGHT = 0.70

# Small seniority adjustment.
SENIORITY_WEIGHT = 0.15
ROLE_WEIGHT = 0.85


SENIORITY_ORDER = {
    "intern": 0,
    "junior": 1,
    "entry": 1,
    "mid": 2,
    "senior": 3,
    "lead": 4,
    "staff": 5,
    "principal": 6,
    "manager": 6,
    "director": 7,
    "unknown": None,
}


def _normalize_seniority(value: str | None) -> str:
    if not value:
        return "unknown"

    value = str(value).strip().lower()

    aliases = {
        "entry-level": "entry",
        "entry level": "entry",
        "new grad": "entry",
        "new graduate": "entry",
        "associate": "junior",
    }

    return aliases.get(value, value)


def _seniority_score(
    candidate_seniority: str | None,
    job_seniority: str | None,
) -> float | None:

    candidate = _normalize_seniority(candidate_seniority)
    job = _normalize_seniority(job_seniority)

    candidate_level = SENIORITY_ORDER.get(candidate)
    job_level = SENIORITY_ORDER.get(job)

    if candidate_level is None or job_level is None:
        return None

    difference = abs(job_level - candidate_level)

    if difference == 0:
        return 100.0

    if difference == 1:
        return 75.0

    if difference == 2:
        return 50.0

    return 25.0


def _resolve_role_family(
    value: str | RoleFamily,
) -> RoleFamily:

    if isinstance(value, RoleFamily):
        return value

    if not value:
        return RoleFamily.UNKNOWN

    return classify_role(str(value))

def _resolve_job_family(job: Job) -> RoleFamily:

    ai_role_family = getattr(job, "role_family", "")
    ai_confidence = float(
        getattr(job, "ai_confidence", 0.0) or 0.0
    )

    if (
        ai_role_family
        and str(ai_role_family).strip().lower()
        not in {"unknown", "other"}
        and ai_confidence >= 0.60
    ):
        return _resolve_role_family(ai_role_family)

    return _resolve_role_family(
        getattr(job, "title", "")
    )


def _role_match_score(
    role: str,
    job_family: RoleFamily,
) -> float:

    if not role or job_family == RoleFamily.UNKNOWN:
        return 0.0

    candidate_family = _resolve_role_family(role)

    if candidate_family == RoleFamily.UNKNOWN:
        return 0.0

    if candidate_family == job_family:
        return 100.0

    return 0.0


def _best_role_score(
    roles: list[str],
    job_family: RoleFamily,
    weight: float,
) -> float | None:

    scores = [
        _role_match_score(role, job_family)
        for role in roles
        if role
    ]

    if not scores:
        return None

    return max(scores) * weight


def calculate_role_score(
    candidate: CandidateProfile,
    job: Job,
) -> float | None:
    """
    Calculate role compatibility from 0–100.

    Priority:
        preferred_roles > secondary_roles > resume_roles

    A role matches when the candidate role and job role resolve
    to the same canonical RoleFamily.

    Returns None when no role preference is configured AND no
    resume roles are available (role is unconfigured).
    Resume roles are facts/evidence, not preferences, but they
    still provide a scoring signal.
    """

    job_family = _resolve_job_family(job)

    if job_family == RoleFamily.UNKNOWN:
        return 0.0

    preferred_roles = list(
        getattr(candidate.preferences, "preferred_roles", []) or []
    )

    secondary_roles = list(
        getattr(candidate.preferences, "secondary_roles", []) or []
    )

    resume_roles = list(
        getattr(candidate.facts, "resume_roles", []) or []
    )

    preferred_score = _best_role_score(
        preferred_roles,
        job_family,
        PREFERRED_WEIGHT,
    )

    secondary_score = _best_role_score(
        secondary_roles,
        job_family,
        SECONDARY_WEIGHT,
    )

    resume_score = _best_role_score(
        resume_roles,
        job_family,
        RESUME_WEIGHT,
    )

    role_scores = [
        score
        for score in (
            preferred_score,
            secondary_score,
            resume_score,
        )
        if score is not None
    ]

    if not role_scores:
        return None

    role_score = max(role_scores)

    seniority_score = _seniority_score(
        getattr(candidate.facts, "career_level", None),
        getattr(job, "seniority", None),
    )

    if seniority_score is not None:
        role_score = (
            role_score * ROLE_WEIGHT
            + seniority_score * SENIORITY_WEIGHT
        )

    return round(
        max(0.0, min(100.0, role_score)),
        2,
    )
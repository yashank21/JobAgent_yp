"""
Job eligibility utilities.

Determines whether a job should be considered for a candidate
before the job is scored and ranked.
"""

import re
from dataclasses import dataclass
from app.location.location_normalizer import normalize_location, location_matches
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
)

@dataclass
class EligibilityResult:
    """
    Result of evaluating whether a job is eligible.
    """

    eligible: bool
    reasons: list[str]


def _normalize(value: str) -> str:
    """Normalize text for matching."""
    return value.strip().lower()


def is_location_eligible(
    candidate: CandidateProfile | list[str],
    job: Job | str,
) -> bool:
    """
    Check if a job's location matches candidate preferences using location_normalizer.
    """
    if isinstance(candidate, list):
        preferred_locations = candidate
    else:
        preferred_locations = getattr(candidate, "preferred_locations", [])

    if isinstance(job, str):
        job_loc = job
    else:
        job_loc = getattr(job, "location", "")

    # Delegate strictly to location_normalizer.py
    return location_matches(job_loc, preferred_locations)


def is_experience_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the candidate meets experience requirements.
    Early-career candidates (<1 year) are given a small buffer (e.g., up to 2 years max required).
    """
    required_experience = getattr(
        job,
        "experience_years_required",
        None,
    )

    if required_experience is None or required_experience <= 0:
        return True

    # Allow early career candidates (0-1 year exp) to match entry/junior roles requesting up to 2 years
    candidate_exp = getattr(candidate, "experience_years", 0)
    max_allowed_req = candidate_exp + (1.5 if candidate_exp <= 1.0 else 0.5)

    return candidate_exp >= required_experience or required_experience <= max_allowed_req


def is_role_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the job matches candidate preferred role families or technical keywords.
    """
    preferred_roles = getattr(candidate, "preferred_roles", [])
    if not preferred_roles:
        return True

    job_title = job.title.lower()
    job_family = classify_role(job.title)

    # Direct keyword fallback for generic titles like "Member of Technical Staff", "Software Engineer", etc.
    tech_keywords = [
        "software", "engineer", "developer", "machine learning", "ml", "ai", 
        "data scientist", "backend", "fullstack", "research", "applied scientist"
    ]
    
    # If role_normalizer classifies it, match family
    for role in preferred_roles:
        candidate_family = classify_role(role)
        if candidate_family != RoleFamily.UNKNOWN and candidate_family == job_family:
            return True

    # Fallback: if family classification failed, check explicit technical keyword presence
    if job_family == RoleFamily.UNKNOWN and any(kw in job_title for kw in tech_keywords):
        return True

    return False


def has_work_authorization_restriction(job: Job) -> bool:
    """
    Detect work-authorization restrictions that exclude Indian candidates.
    """
    text = _normalize(getattr(job, "description", ""))

    patterns = [
        r"\bitar\b",
        r"u\.s\. citizen",
        r"us citizen",
        r"u\.s\. citizenship",
        r"us citizenship",
        r"permanent resident",
        r"green card",
        r"must be located in the us",
        r"authorized to work in the united states",
    ]

    return any(re.search(pattern, text) for pattern in patterns)


def is_work_authorization_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Reject jobs that strictly demand US citizenship/ITAR for non-US candidate profiles.
    """
    pref_locs = [p.lower() for p in getattr(candidate, "preferred_locations", [])]
    is_india_focused = any("india" in loc or "bengaluru" in loc or "pune" in loc for loc in pref_locs)

    # If candidate is looking for India/Remote roles and the job mandates US citizenship/ITAR -> Reject
    if is_india_focused and has_work_authorization_restriction(job):
        return False

    return True


def check_eligibility(
    candidate: CandidateProfile,
    job: Job,
) -> EligibilityResult:
    """
    Run all hard eligibility checks and return detailed reasons.
    """
    reasons: list[str] = []

    # 1. Location Check
    if not is_location_eligible(candidate, job):
        reasons.append("outside preferred locations")

    # 2. Work Authorization Check
    if not is_work_authorization_eligible(candidate, job):
        reasons.append("work authorization restriction (US/ITAR strictly required)")

    # 3. Role Check
    if not is_role_eligible(candidate, job):
        reasons.append("does not match preferred roles")

    # 4. Experience Check
    if not is_experience_eligible(candidate, job):
        required_experience = getattr(job, "experience_years_required", None)
        if required_experience is not None:
            reasons.append(f"{required_experience:g}+ years experience required")
        else:
            reasons.append("experience requirement not met")

    return EligibilityResult(
        eligible=len(reasons) == 0,
        reasons=reasons,
    )


def is_job_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> EligibilityResult:
    """
    Backward-compatible alias for check_eligibility().
    """
    return check_eligibility(candidate, job)
"""
Job eligibility utilities.

Determines whether a job should be considered for a candidate
before the job is scored and ranked.

IMPORTANT DESIGN:

Eligibility should handle HARD disqualifiers only.

Experience gaps and seniority mismatches are NOT automatically
hard rejection criteria. Those should be handled by the scoring
and ranking layer so that promising jobs are not discarded too early.
"""

import re
from dataclasses import dataclass

from app.location.location_normalizer import location_matches
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
)
from app.eligibility.seniority import classify_seniority


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


# ============================================================
# OBVIOUS NON-TARGET ROLES
# ============================================================

NON_ENGINEERING_TITLE_PATTERNS = [
    # Sales
    r"\bsales\b",
    r"\bsales specialist\b",
    r"\baccount executive\b",
    r"\baccount manager\b",
    r"\bbusiness development\b",
    r"\bbdr\b",
    r"\bsdr\b",

    # Business / operations
    r"\bbusiness analyst\b",
    r"\bbusiness operations\b",
    r"\boperations analyst\b",
    r"\bprogram manager\b",

    # Product
    r"\bproduct manager\b",
    r"\bproduct management\b",

    # Management
    r"\bengineering manager\b",
    r"\bsoftware engineering manager\b",
    r"\bengineering director\b",
    r"\bhead of engineering\b",
    r"\bvp of engineering\b",

    # Support / customer-facing
    r"\bcustomer success\b",
    r"\bcustomer support\b",
    r"\btechnical support\b",
    r"\bsupport specialist\b",
    
    r"\baccountant\b",
    r"\bfinancial analyst\b",
    r"\bfinance\b",
    r"\bhuman resources\b",
    r"\brecruiter\b",
    r"\brecruiting\b",
    r"\blegal counsel\b",
    r"\battorney\b",
    r"\bmarketing\b",
    r"\bcommunications\b",
    r"\bprocurement\b",
    r"\bsourcing\b",
    r"\boperations\b",
]


def is_obvious_non_engineering_role(
    job: Job,
) -> bool:
    """
    Detect job titles that are clearly outside the candidate's
    engineering-oriented target roles.

    This is intentionally conservative.

    Unknown engineering titles are NOT rejected here.
    Only obvious non-target occupations are rejected.
    """

    title = _normalize(
        getattr(job, "title", "")
    )

    if not title:
        return False

    return any(
        re.search(
            pattern,
            title,
        )
        for pattern in NON_ENGINEERING_TITLE_PATTERNS
    )


# ============================================================
# LOCATION
# ============================================================

def is_location_eligible(
    candidate: CandidateProfile | list[str],
    job: Job | str,
) -> bool:
    """
    Check if a job's location matches candidate preferences.
    """

    if isinstance(candidate, list):
        preferred_locations = candidate
    else:
        preferred_locations = getattr(
            candidate.preferences,
            "preferred_locations",
            [],
        )

    if isinstance(job, str):
        job_location = job
        remote_type = ""
    else:
        job_location = getattr(
            job,
            "location",
            "",
        )

        remote_type = getattr(
            job,
            "remote_type",
            "",
        )

    return location_matches(
        job_location,
        preferred_locations,
        remote_type,
    )


# ============================================================
# EXPERIENCE
# ============================================================

def is_experience_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the candidate meets the job's minimum
    experience requirement.

    A small tolerance is allowed for early-career candidates.

    Example:

        Candidate: 11 months
        Required:  1 year
        -> eligible

        Candidate: 11 months
        Required:  2 years
        -> NOT eligible

        Candidate: 11 months
        Required:  4 years
        -> NOT eligible

        No experience requirement
        -> eligible
    """

    required_experience = getattr(
        job,
        "experience_years_required",
        None,
    )

    if required_experience is None:
        return True

    if required_experience <= 0:
        return True

    candidate_experience = getattr(
        candidate.facts,
        "experience_years",
        0.0,
    )

    # --------------------------------------------------------
    # Early-career tolerance
    #
    # 11 months should not be rejected for a 1-year posting.
    # But this tolerance must NOT make 2/3/4-year jobs eligible.
    # --------------------------------------------------------

    if (
        candidate_experience >= 0.75
        and required_experience <= 1.0
    ):
        return True

    return candidate_experience >= required_experience


# ============================================================
# ROLE
# ============================================================

def is_role_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the job belongs to a role family compatible
    with at least one candidate role.

    Primary and secondary roles are considered.

    Role compatibility here is intentionally conservative:
    eligibility only determines whether the role is broadly
    relevant. Detailed scoring belongs to role_scorer.py.
    """

    preferred_roles = list(
        getattr(
            candidate.preferences,
            "preferred_roles",
            [],
        )
        or []
    )

    secondary_roles = list(
        getattr(
            candidate.preferences,
            "secondary_roles",
            [],
        )
        or []
    )

    # No explicit role intent means role is not a hard filter.
    if not preferred_roles and not secondary_roles:
        return True

    # Reject clearly unrelated occupations.
    if is_obvious_non_engineering_role(job):
        return False

    job_family = classify_role(
        getattr(
            job,
            "title",
            "",
        )
    )

    if job_family == RoleFamily.UNKNOWN:
        return False

    candidate_roles = (
        preferred_roles
        + secondary_roles
    )

    for role in candidate_roles:

        candidate_family = classify_role(
            str(role)
        )

        if candidate_family == RoleFamily.UNKNOWN:
            continue

        # Eligibility only asks:
        # "Is this broadly the same role family?"
        if candidate_family == job_family:
            return True

    return False


# ============================================================
# WORK AUTHORIZATION
# ============================================================

def has_work_authorization_restriction(
    job: Job,
) -> bool:
    """
    Detect explicit work-authorization restrictions.

    We intentionally focus on strong restrictions such as:

        - US citizenship
        - ITAR
        - permanent residency
        - green card
        - explicit US citizenship requirement

    Generic wording such as "authorized to work in the US"
    is not automatically treated as a hard rejection because
    that can be contextual and location-dependent.
    """

    text = _normalize(
        getattr(
            job,
            "description",
            "",
        )
    )

    patterns = [
        r"\bitar\b",

        r"\bu\.s\. citizen\b",
        r"\bus citizen\b",
        r"\bu\.s\. citizens\b",
        r"\bus citizens\b",

        r"\bu\.s\. citizenship\b",
        r"\bus citizenship\b",

        r"\bpermanent resident\b",
        r"\bgreen card\b",

        r"\bmust be a u\.s\. citizen\b",
        r"\bmust be a us citizen\b",

        r"\bcitizenship required\b",

        r"\bsecurity clearance required\b",
    ]

    return any(
        re.search(
            pattern,
            text,
        )
        for pattern in patterns
    )


def is_work_authorization_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Reject jobs with explicit restrictions that clearly prevent
    the candidate from applying.

    Work authorization remains a HARD eligibility check.
    """

    preferred_locations = [
        location.lower()
        for location in getattr(
            candidate.preferences,
            "preferred_locations",
            [],
        )
    ]

    is_india_focused = any(
        "india" in location
        or "bengaluru" in location
        or "bangalore" in location
        or "hyderabad" in location
        or "pune" in location
        or "gurugram" in location
        or "noida" in location
        for location in preferred_locations
    )

    if (
        is_india_focused
        and has_work_authorization_restriction(job)
    ):
        return False

    return True


# ============================================================
# SENIORITY
# ============================================================

def is_seniority_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Seniority is NOT a hard rejection criterion.

    Senior / Manager / Principal jobs remain visible but should
    receive strong penalties during scoring.

    This is important because job titles are noisy and companies
    frequently use inflated titles.
    """

    return True


# ============================================================
# COMPLETE ELIGIBILITY CHECK
# ============================================================

def check_eligibility(
    candidate: CandidateProfile,
    job: Job,
) -> EligibilityResult:
    """
    Run HARD eligibility checks.

    Experience and seniority are intentionally excluded from
    hard rejection.
    """

    reasons: list[str] = []

    # --------------------------------------------------------
    # 1. Location
    # --------------------------------------------------------

    if not is_location_eligible(
        candidate,
        job,
    ):
        reasons.append(
            "outside preferred locations"
        )

    # --------------------------------------------------------
    # 2. Work authorization
    # --------------------------------------------------------

    if not is_work_authorization_eligible(
        candidate,
        job,
    ):
        reasons.append(
            "work authorization restriction "
            "(US/ITAR strictly required)"
        )

    # --------------------------------------------------------
    # 3. Role
    # --------------------------------------------------------

    if not is_role_eligible(
        candidate,
        job,
    ):
        reasons.append(
            "does not match preferred roles"
        )

    # --------------------------------------------------------
    # 4. Experience
    #
    # NOT HARD REJECTION
    # --------------------------------------------------------

    required_experience = getattr(
        job,
        "experience_years_required",
        None,
    )

    candidate_experience = getattr(
        candidate.facts,
        "experience_years",
        0.0,
    )

    if (
        required_experience is not None
        and required_experience > candidate_experience
    ):
        reasons.append(
            f"experience gap: "
            f"{required_experience:g}+ years required "
            f"(candidate: {candidate_experience:.1f} years)"
        )

    # --------------------------------------------------------
    # 5. Seniority
    #
    # NOT HARD REJECTION
    # --------------------------------------------------------

    seniority = classify_seniority(
        job.title
    )

    if seniority in {
        "senior",
        "manager",
        "principal",
        "staff",
        "director",
        "lead",
    }:
        reasons.append(
            f"seniority: {seniority}"
        )

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Only TRUE hard rejection reasons determine eligibility.
    #
    # Experience and seniority warnings do NOT make a job
    # ineligible.
    # --------------------------------------------------------

    hard_reasons = []

    for reason in reasons:

        if (
            reason == "outside preferred locations"
            or reason.startswith(
                "work authorization restriction"
            )
            or reason == "does not match preferred roles"
        ):
            hard_reasons.append(reason)

    return EligibilityResult(
        eligible=len(hard_reasons) == 0,
        reasons=reasons,
    )


# ============================================================
# BACKWARD COMPATIBILITY
# ============================================================

def is_job_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> EligibilityResult:
    """
    Backward-compatible alias for check_eligibility().
    """

    return check_eligibility(
        candidate,
        job,
    )

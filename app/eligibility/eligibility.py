"""
Job eligibility utilities.

Determines whether a job should be considered for a candidate
before the job is scored and ranked.
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
            candidate,
            "preferred_locations",
            [],
        )

    if isinstance(job, str):
        job_location = job
    else:
        job_location = getattr(
            job,
            "location",
            "",
        )

    return location_matches(
        job_location,
        preferred_locations,
    )


def is_experience_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the candidate meets the job's minimum
    experience requirement.

    Eligibility is a hard requirement.

    Unlike the scoring layer, we do NOT give the candidate
    an artificial experience buffer.

    Examples:

        Candidate: 2 years
        Required:  2 years
        -> eligible

        Candidate: 3 years
        Required:  2 years
        -> eligible

        Candidate: 1 year
        Required:  2 years
        -> NOT eligible

        No experience requirement
        -> eligible
    """

    required_experience = getattr(
        job,
        "experience_years_required",
        None,
    )

    # No explicit requirement.
    if required_experience is None:
        return True

    # Zero or negative means no minimum experience.
    if required_experience <= 0:
        return True

    candidate_experience = getattr(
        candidate,
        "experience_years",
        0.0,
    )

    return candidate_experience >= required_experience


def is_role_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the job matches candidate preferred role families
    or technical keywords.
    """

    preferred_roles = getattr(
        candidate,
        "preferred_roles",
        [],
    )

    if not preferred_roles:
        return True

    job_title = (
        job.title or ""
    ).lower()

    job_family = classify_role(
        job.title
    )

        # Compare the job's role family with the
    # candidate's preferred role families.

    for role in preferred_roles:

        candidate_family = classify_role(
            role
        )

        if (
            candidate_family != RoleFamily.UNKNOWN
            and candidate_family == job_family
        ):
            return True

    return False


def has_work_authorization_restriction(
    job: Job,
) -> bool:
    """
    Detect work-authorization restrictions that exclude
    Indian candidates.
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
        r"u\.s\. citizen",
        r"us citizen",
        r"u\.s\. citizenship",
        r"us citizenship",
        r"permanent resident",
        r"green card",
        r"must be located in the us",
        r"authorized to work in the united states",
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
    Reject jobs that strictly demand US citizenship/ITAR
    for non-US candidate profiles.
    """

    preferred_locations = [
        location.lower()
        for location in getattr(
            candidate,
            "preferred_locations",
            [],
        )
    ]

    is_india_focused = any(
        "india" in location
        or "bengaluru" in location
        or "pune" in location
        for location in preferred_locations
    )

    if (
        is_india_focused
        and has_work_authorization_restriction(job)
    ):
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
    # --------------------------------------------------------

    if not is_experience_eligible(
        candidate,
        job,
    ):
        required_experience = getattr(
            job,
            "experience_years_required",
            None,
        )

        if required_experience is not None:
            reasons.append(
                f"{required_experience:g}+ years experience required"
            )
        else:
            reasons.append(
                "experience requirement not met"
            )
    # --------------------------------------------------------
    # 5. Seniority
    # --------------------------------------------------------

    if not is_seniority_eligible(
        candidate,
        job,
    ):
        reasons.append(
            "job seniority is above candidate level"
        )
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

    return check_eligibility(
        candidate,
        job,
    )
    
def is_seniority_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Reject jobs clearly above the candidate's current seniority.
    """

    seniority = classify_seniority(job.title)

    # Current candidate is early-career.
    if candidate.experience_years < 2.0:
        return seniority not in {
            "senior",
            "manager",
        }

    return True
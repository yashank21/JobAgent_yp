"""
Backward-compatible eligibility service.

The canonical eligibility implementation lives in:

    app.eligibility.eligibility
"""

from app.eligibility.eligibility import (
    EligibilityResult,
    check_eligibility,
    has_work_authorization_restriction,
    is_experience_eligible as _is_experience_eligible,
    is_location_eligible as _is_location_eligible,
    is_job_eligible as _is_job_eligible,
    is_work_authorization_eligible as _is_work_authorization_eligible,
)

from app.models.candidate import CandidateProfile
from app.models.job import Job


def is_location_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check only location eligibility.
    """

    return _is_location_eligible(
        candidate,
        job,
    )


def is_experience_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check only experience eligibility.
    """

    return _is_experience_eligible(
        candidate,
        job,
    )


def is_job_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Backward-compatible boolean API.

    New code should use check_eligibility().
    """

    return _is_job_eligible(
        candidate,
        job,
    )


def is_work_authorization_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Currently treated as a warning rather than
    a hard eligibility failure.
    """

    return _is_work_authorization_eligible(
        candidate,
        job,
    )


__all__ = [
    "EligibilityResult",
    "check_eligibility",
    "has_work_authorization_restriction",
    "is_location_eligible",
    "is_experience_eligible",
    "is_job_eligible",
    "is_work_authorization_eligible",
]
"""
Job eligibility utilities.

Determines whether a job should be considered for a candidate
before the job is scored and ranked.
"""

import re

from app.models.candidate import CandidateProfile
from app.models.job import Job


def _normalize(value: str) -> str:
    """Normalize text for matching."""
    return value.strip().lower()


def is_location_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the job location is acceptable.

    A job is eligible when:
    - The candidate has no preferred-location restrictions.
    - The job is remote.
    - The job location matches one of the candidate's
      preferred locations.
    """

    if not candidate.preferred_locations:
        return True

    location = _normalize(job.location)
    remote_type = _normalize(job.remote_type)

    if "remote" in location or "remote" in remote_type:
        return True

    for preferred_location in candidate.preferred_locations:
        preferred = _normalize(preferred_location)

        if preferred in location:
            return True

    return False


def is_experience_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the candidate has enough experience.

    If the job has no parsed experience requirement,
    do not reject the job.
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

    return (
        candidate.experience_years
        >= required_experience
    )


def has_work_authorization_restriction(
    job: Job,
) -> bool:
    """
    Detect obvious work-authorization restrictions
    from the job description.

    This is deliberately conservative.
    """

    text = _normalize(job.description)

    patterns = [
        r"\bitar\b",
        r"u\.s\. citizen",
        r"us citizen",
        r"u\.s\. citizenship",
        r"us citizenship",
        r"permanent resident",
        r"green card",
        r"lawful permanent resident",
        r"work authorization",
        r"authorized to work in the united states",
    ]

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def is_work_authorization_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Determine whether obvious work-authorization
    restrictions should disqualify the job.

    CandidateProfile currently does not contain a
    work-authorization field, so we cannot make a
    definitive authorization decision yet.

    Therefore this function currently returns True
    and leaves the restriction available as a warning.
    """

    return True


def is_job_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Determine whether a job passes the current
    hard eligibility checks.
    """

    if not is_location_eligible(
        candidate,
        job,
    ):
        return False

    if not is_experience_eligible(
        candidate,
        job,
    ):
        return False

    if not is_work_authorization_eligible(
        candidate,
        job,
    ):
        return False

    return True
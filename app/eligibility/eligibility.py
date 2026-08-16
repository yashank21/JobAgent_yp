"""
Job eligibility utilities.

Determines whether a job is realistically applicable
to the candidate before ranking it.
"""

from dataclasses import dataclass

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
)


@dataclass
class EligibilityResult:
    eligible: bool
    reasons: list[str]


def _normalize(value: str) -> str:
    return value.strip().lower()


def _location_matches(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the job location is compatible
    with the candidate's preferred locations.

    Remote jobs are considered compatible with any
    candidate location preference.
    """

    if not candidate.preferred_locations:
        return True

    job_location = _normalize(job.location)
    remote_type = _normalize(job.remote_type)

    # Remote jobs are universally location-compatible.
    if (
        job_location == "remote"
        or "remote" in remote_type
    ):
        return True

    for preferred in candidate.preferred_locations:

        preferred_normalized = _normalize(preferred)

        if (
            preferred_normalized
            and preferred_normalized in job_location
        ):
            return True

    return False


def _role_matches(
    candidate: CandidateProfile,
    job: Job,
) -> bool:
    """
    Check whether the job belongs to one of the
    candidate's preferred role families.

    Role-family matching allows:

        Software Engineer
        Software Development Engineer
        New Graduate Engineer, Software

    to resolve to the same software-engineering family.
    """

    if not candidate.preferred_roles:
        return True

    job_family = classify_role(job.title)

    if job_family == RoleFamily.UNKNOWN:
        return False

    for preferred_role in candidate.preferred_roles:

        preferred_family = classify_role(
            preferred_role
        )

        if (
            preferred_family != RoleFamily.UNKNOWN
            and preferred_family == job_family
        ):
            return True

    return False


def is_job_eligible(
    candidate: CandidateProfile,
    job: Job,
) -> EligibilityResult:
    """
    Determine whether a job passes hard eligibility checks.

    Hard checks:

    - Preferred role family
    - Location compatibility
    - Experience requirement

    Salary and skill matching remain soft scoring criteria.
    """

    reasons: list[str] = []

    # -----------------------------------------
    # Role
    # -----------------------------------------

    if not _role_matches(candidate, job):

        reasons.append(
            f"Job role '{job.title}' does not match "
            "preferred roles."
        )

    # -----------------------------------------
    # Location
    # -----------------------------------------

    if not _location_matches(candidate, job):

        reasons.append(
            f"Location '{job.location}' is outside "
            "preferred locations."
        )

    # -----------------------------------------
    # Experience
    # -----------------------------------------

    required_experience = getattr(
        job,
        "experience_years_required",
        None,
    )

    if (
        required_experience is not None
        and required_experience > 0
        and candidate.experience_years
        < required_experience
    ):
        reasons.append(
            f"Requires {required_experience}+ years of "
            f"experience; candidate has "
            f"{candidate.experience_years:.2f} years."
        )

    return EligibilityResult(
        eligible=len(reasons) == 0,
        reasons=reasons,
    )


def check_eligibility(
    candidate: CandidateProfile,
    job: Job,
) -> EligibilityResult:
    """
    Backward-compatible eligibility API.

    Delegates to is_job_eligible().
    """

    return is_job_eligible(
        candidate,
        job,
    )
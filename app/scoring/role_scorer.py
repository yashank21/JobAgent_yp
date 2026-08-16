"""
Role scoring utilities.

Scores how well a job title matches the candidate's preferred roles.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
)


def calculate_role_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate how well the job title matches the candidate's
    preferred roles.

    Returns a score from 0.0 to 100.0.

    Role classification is delegated entirely to
    role_normalizer.py so that eligibility, scoring,
    and explanations all use the same role taxonomy.
    """

    if not candidate.preferred_roles:
        return 0.0

    job_family = classify_role(job.title)

    if job_family == RoleFamily.UNKNOWN:
        return 0.0

    for preferred_role in candidate.preferred_roles:

        preferred_family = classify_role(
            preferred_role
        )

        if (
            preferred_family != RoleFamily.UNKNOWN
            and preferred_family == job_family
        ):
            return 100.0

    return 0.0
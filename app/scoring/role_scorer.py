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


ROLE_TO_FAMILY = {
    "software engineer": RoleFamily.SOFTWARE_ENGINEERING,
    "machine learning engineer": RoleFamily.MACHINE_LEARNING,
    "ml engineer": RoleFamily.MACHINE_LEARNING,
    "data engineer": RoleFamily.DATA_ENGINEERING,
    "backend engineer": RoleFamily.BACKEND_ENGINEERING,
    "frontend engineer": RoleFamily.FRONTEND_ENGINEERING,
    "devops engineer": RoleFamily.DEVOPS,
}


def calculate_role_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate how well the job title matches the candidate's
    preferred roles.

    Returns a score from 0.0 to 100.0.
    """

    if not candidate.preferred_roles:
        return 0.0

    job_family = classify_role(job.title)

    if job_family == RoleFamily.UNKNOWN:
        return 0.0

    for role in candidate.preferred_roles:
        role_key = role.lower().strip()

        candidate_family = ROLE_TO_FAMILY.get(role_key)

        if candidate_family == job_family:
            return 100.0

    return 0.0
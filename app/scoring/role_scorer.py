"""
Role scoring utilities.

Scores how well a job title matches the candidate's preferred roles.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job


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

    job_title = job.title.lower().strip()

    for role in candidate.preferred_roles:
        role_lower = role.lower().strip()

        if role_lower and role_lower in job_title:
            return 100.0

    return 0.0
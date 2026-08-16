"""
Experience scoring utilities.

Scores how well a candidate's experience matches
the experience requirement of a job.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.services.experience_parser import parse_experience_years


def calculate_experience_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate the candidate's experience match score.

    Returns a score between 0 and 100.

    Rules:
    - No experience requirement -> 100
    - Candidate meets requirement -> 100
    - Candidate has less experience -> proportional score
    - No candidate experience -> 0
    """

    required_years = parse_experience_years(
        job.experience_required
    )

    # Job does not specify an experience requirement.
    if required_years is None:
        return 100.0

    # Defensive handling for invalid requirements.
    if required_years <= 0:
        return 100.0

    candidate_years = max(
        candidate.experience_years,
        0.0,
    )

    if candidate_years >= required_years:
        return 100.0

    return (
        candidate_years / required_years
    ) * 100
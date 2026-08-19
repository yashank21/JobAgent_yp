"""
Job scoring utilities.

Scores how well a job matches a candidate profile.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.services.skill_normalizer import normalize_skills


def calculate_skill_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate skill alignment.

    Required skills dominate the score.
    Preferred skills provide a smaller contribution.

    Required skills: 70%
    Preferred skills: 30%
    """

    candidate_skills = normalize_skills(
        candidate.skills
    )

    required_skills = normalize_skills(
        job.required_skills
    )

    preferred_skills = normalize_skills(
        job.preferred_skills
    )

    if not required_skills and not preferred_skills:
        return 0.0

    required_score = 0.0

    if required_skills:
        matched_required = (
            required_skills & candidate_skills
        )

        required_score = (
            len(matched_required)
            / len(required_skills)
        ) * 100.0

    preferred_score = 0.0

    if preferred_skills:
        matched_preferred = (
            preferred_skills & candidate_skills
        )

        preferred_score = (
            len(matched_preferred)
            / len(preferred_skills)
        ) * 100.0

    score = (
        required_score * 0.70
        + preferred_score * 0.30
    )

    return round(score, 2)
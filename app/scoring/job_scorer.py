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
    Calculate the candidate's skill match score for a job.

    Required skills carry more weight than preferred skills.

    Required skills: 70%
    Preferred skills: 30%

    Skill aliases are normalized before comparison.
    """

    candidate_skills = normalize_skills(
        candidate.facts.skills
    )

    required_skills = normalize_skills(
        job.required_skills
    )

    preferred_skills = normalize_skills(
        job.preferred_skills
    )

    # Missing skill lists mean "unknown", not "no overlap".
    # Groq/rate-limit failures must not crush an otherwise
    # strong role match.
    if not required_skills and not preferred_skills:
        return 50.0

    required_score = 0.0

    if required_skills:
        matched_required = (
            required_skills & candidate_skills
        )

        required_score = (
            len(matched_required)
            / len(required_skills)
        )

    preferred_score = 0.0

    if preferred_skills:
        matched_preferred = (
            preferred_skills & candidate_skills
        )

        preferred_score = (
            len(matched_preferred)
            / len(preferred_skills)
        )

    return (
        required_score * 0.7
        + preferred_score * 0.3
    ) * 100

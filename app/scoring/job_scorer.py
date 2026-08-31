"""
Job scoring utilities.

Scores how well a job matches a candidate profile.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.services.skill_normalizer import normalize_skills


def _normalize(value: str) -> str:
    """Normalize text for case-insensitive matching."""
    return value.strip().lower()


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
        candidate.skills
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


def calculate_experience_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Score the candidate's experience against the job requirement.

    Full score when candidate experience meets or exceeds
    the required experience.

    Partial score when the candidate has some relevant experience.
    """

    required_experience = getattr(
        job,
        "experience_years_required",
        None,
    )

    if required_experience is None:
        return 100.0

    if required_experience <= 0:
        return 100.0

    candidate_experience = candidate.experience_years

    if candidate_experience >= required_experience:
        return 100.0

    return (
        candidate_experience
        / required_experience
    ) * 100


def calculate_role_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """Score how well the job title matches preferred roles."""

    if not candidate.preferred_roles:
        return 100.0

    job_title = _normalize(job.title)

    for role in candidate.preferred_roles:
        if _normalize(role) in job_title:
            return 100.0

    return 0.0


def calculate_location_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """Score whether the job location matches candidate preferences."""

    if not candidate.preferred_locations:
        return 100.0

    job_location = _normalize(job.location)

    for location in candidate.preferred_locations:
        if _normalize(location) in job_location:
            return 100.0

    return 0.0


def calculate_salary_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Score whether the job satisfies the candidate's minimum salary.

    If no salary information exists, don't punish the job.
    """

    minimum_salary = candidate.minimum_salary_lpa

    if minimum_salary <= 0:
        return 100.0

    if job.salary_max_lpa is None:
        return 100.0

    if job.salary_max_lpa >= minimum_salary:
        return 100.0

    return (
        job.salary_max_lpa
        / minimum_salary
    ) * 100
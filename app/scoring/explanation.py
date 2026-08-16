"""
Match explanation utilities.

Explains why a candidate matches or does not match a job.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job


def _normalize(value: str) -> str:
    """Normalize text for case-insensitive matching."""
    return value.strip().lower()


def explain_skill_match(
    candidate: CandidateProfile,
    job: Job,
) -> list[str]:
    """
    Explain required and preferred skill matches.
    """

    candidate_skills = {
        _normalize(skill)
        for skill in candidate.skills
    }

    explanations = []

    for skill in job.required_skills:

        normalized = _normalize(skill)

        if normalized in candidate_skills:
            explanations.append(
                f"✓ {skill} — required"
            )
        else:
            explanations.append(
                f"✗ {skill} — required skill missing"
            )

    for skill in job.preferred_skills:

        normalized = _normalize(skill)

        if normalized in candidate_skills:
            explanations.append(
                f"✓ {skill} — preferred"
            )

    return explanations


def explain_role_match(
    candidate: CandidateProfile,
    job: Job,
) -> str:
    """Explain role compatibility."""

    if not candidate.preferred_roles:
        return "✓ No preferred role restriction"

    job_title = _normalize(job.title)

    for role in candidate.preferred_roles:

        if _normalize(role) in job_title:
            return (
                f"✓ Role matches preferred role: "
                f"{role}"
            )

    return "✗ Job title does not match preferred roles"


def explain_location_match(
    candidate: CandidateProfile,
    job: Job,
) -> str:
    """Explain location compatibility."""

    if not candidate.preferred_locations:
        return "✓ No preferred location restriction"

    job_location = _normalize(job.location)

    # Remote jobs are compatible with candidates
    # who allow remote work.
    if "remote" in job_location:
        return "✓ Remote job"

    for location in candidate.preferred_locations:

        normalized = _normalize(location)

        if normalized in job_location:
            return (
                f"✓ Location matches preference: "
                f"{location}"
            )

    return "✗ Job is outside preferred locations"


def explain_experience_match(
    candidate: CandidateProfile,
    job: Job,
) -> str:
    """Explain experience compatibility."""

    required = getattr(
        job,
        "experience_years_required",
        None,
    )

    if required is None or required <= 0:
        return "✓ Experience: No explicit requirement"

    candidate_experience = candidate.experience_years

    if candidate_experience >= required:
        return (
            f"✓ Experience requirement met "
            f"({candidate_experience:.2f} / "
            f"{required:.2f} years)"
        )

    return (
        f"✗ Experience requirement not met "
        f"({candidate_experience:.2f} / "
        f"{required:.2f} years)"
    )


def explain_salary_match(
    candidate: CandidateProfile,
    job: Job,
) -> str:
    """Explain salary compatibility."""

    minimum = candidate.minimum_salary_lpa

    if minimum <= 0:
        return "✓ No minimum salary requirement"

    if job.salary_max_lpa is None:
        return "⚠ Salary information unavailable"

    if job.salary_max_lpa >= minimum:
        return (
            f"✓ Salary meets minimum requirement "
            f"(₹{job.salary_max_lpa:.2f} LPA max)"
        )

    return (
        f"✗ Salary below minimum requirement "
        f"(₹{job.salary_max_lpa:.2f} LPA max)"
    )


def explain_match(
    candidate: CandidateProfile,
    job: Job,
) -> list[str]:
    """
    Generate a complete human-readable explanation
    for a candidate-job match.
    """

    explanations = []

    explanations.extend(
        explain_skill_match(
            candidate,
            job,
        )
    )

    explanations.append(
        explain_role_match(
            candidate,
            job,
        )
    )

    explanations.append(
        explain_location_match(
            candidate,
            job,
        )
    )

    explanations.append(
        explain_experience_match(
            candidate,
            job,
        )
    )

    explanations.append(
        explain_salary_match(
            candidate,
            job,
        )
    )

    return explanations
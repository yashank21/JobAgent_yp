"""
Match explanation utilities.

Explains why a candidate matches or does not match a job.
"""

from app.location.location_normalizer import (
    location_matches,
    normalize_location,
)
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
)


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
        for skill in candidate.facts.skills
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
    """Explain role compatibility using role-family classification."""

    preferred = list(candidate.preferences.preferred_roles or [])
    secondary = list(getattr(candidate.preferences, "secondary_roles", []) or [])
    resume_roles = list(candidate.facts.resume_roles or [])

    if not preferred and not secondary:
        if not resume_roles:
            return "⚠ Role preference not configured"
        return "⚠ Role preference not configured (resume evidence only)"

    job_family = classify_role(job.title)

    for role in preferred:
        if classify_role(role) == job_family and job_family != RoleFamily.UNKNOWN:
            return f"✓ Role matches preferred role: {role}"

    for role in secondary:
        if classify_role(role) == job_family and job_family != RoleFamily.UNKNOWN:
            return f"✓ Role matches secondary target: {role}"

    for role in resume_roles:
        if classify_role(role) == job_family and job_family != RoleFamily.UNKNOWN:
            return f"✓ Role matches resume evidence: {role}"

    return "✗ Job title does not match preferred roles"


def explain_location_match(
    candidate: CandidateProfile,
    job: Job,
) -> str:
    """Explain location compatibility."""

    if not candidate.preferences.preferred_locations:
        return "⚠ Location preference not configured"

    normalized_job = normalize_location(
        job.location
    )

    remote_type = getattr(
        job,
        "remote_type",
        "",
    )

    is_remote_job = (
        normalized_job == "Remote"
        or "remote" in remote_type.lower()
    )

    # ------------------------------------------------------------
    # Remote job
    # ------------------------------------------------------------

    if is_remote_job:

        for location in candidate.preferences.preferred_locations:

            normalized_pref = normalize_location(
                location
            )

            if normalized_pref in {
                "Remote",
                "India",
            }:
                return (
                    f"✓ Remote job matches preference: "
                    f"{location}"
                )

        return (
            f"✗ Remote job is outside preferred locations "
            f"({job.location})"
        )

    # ------------------------------------------------------------
    # Normal location matching
    # ------------------------------------------------------------

    if location_matches(
    job.location,
    candidate.preferences.preferred_locations,
    job.remote_type,
    ):
        return (
            f"✓ Location matches preference: "
            f"{normalized_job}"
        )

    # ------------------------------------------------------------
    # US-specific explanation
    # ------------------------------------------------------------

    normalized_preferences = [
        normalize_location(location)
        for location in candidate.preferences.preferred_locations
    ]

    if (
        normalized_job == "United States"
        and "United States" not in normalized_preferences
    ):
        return (
            f"✗ Job is in the US "
            f"({job.location}), outside preferred locations"
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

    candidate_experience = candidate.facts.experience_years

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

    minimum = candidate.preferences.minimum_salary_lpa

    if minimum is None:
        return "⚠ Salary preference not configured"

    if minimum <= 0:
        return "⚠ Salary preference not configured"

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

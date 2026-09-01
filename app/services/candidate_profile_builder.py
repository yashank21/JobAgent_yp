"""
Candidate profile builder.

Builds a CandidateProfile from resume-derived signals.

This module separates:
    - facts extracted from the resume
    - preferences explicitly configured by the user

Resume-derived data may populate:
    - skills
    - resume_roles
    - experience_years
    - career_level

User preferences must remain untouched.
"""

from app.models.candidate import CandidateProfile
from app.services.resume_classifier import classify_resume


def build_candidate_profile(
    resume_text: str,
    base_profile: CandidateProfile | None = None,
) -> CandidateProfile:
    """
    Build a CandidateProfile using deterministic resume classification.

    If base_profile is provided, resume-derived fields are updated while
    explicit user preferences are preserved.

    If no base_profile is provided, a fresh CandidateProfile is created.
    """

    classification = classify_resume(
        resume_text,
    )

    profile = base_profile or CandidateProfile()

    # ---------------------------------------------------------
    # Resume-derived facts
    # ---------------------------------------------------------

    profile.facts.skills = list(
        classification.skills
    )

    profile.facts.resume_roles = list(
        classification.role_titles
    )

    profile.facts.experience_years = (
        classification.experience_years
    )

    profile.facts.career_level = (
        classification.career_level
    )

    return profile
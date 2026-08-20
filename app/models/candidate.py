"""
Candidate profile model.

Represents the candidate information used by the
job-matching pipeline.
"""

from dataclasses import dataclass, field


@dataclass
class CandidateProfile:

    # -----------------------------
    # Basic identity
    # -----------------------------

    name: str = ""
    email: str = ""
    location: str = ""

    # -----------------------------
    # Experience
    # -----------------------------

    experience_years: float = 0.0

        # -----------------------------
    # Preferences
    # -----------------------------

    preferred_roles: list[str] = field(
        default_factory=list
    )

    secondary_roles: list[str] = field(
        default_factory=list
    )

    preferred_locations: list[str] = field(
        default_factory=list
    )

    # -----------------------------
    # Technical skills
    # -----------------------------

    skills: list[str] = field(
        default_factory=list
    )

    # -----------------------------
    # Education
    # -----------------------------

    education: list[str] = field(
        default_factory=list
    )

    # -----------------------------
    # Projects
    # -----------------------------

    projects: list[str] = field(
        default_factory=list
    )

    # -----------------------------
    # Compensation
    # -----------------------------

    minimum_salary_lpa: float = 0.0

    # -----------------------------
    # Links
    # -----------------------------

    github_url: str = ""
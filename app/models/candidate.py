"""
Candidate profile model.

Represents a user independently of the ranking system.

The profile contains:

- Identity
- Experience
- Career intent
- Skills
- Education/projects
- Job preferences
"""

from dataclasses import dataclass, field


@dataclass
class CandidateProfile:

    # ============================================================
    # IDENTITY
    # ============================================================

    name: str = ""
    email: str = ""
    location: str = ""

    # ============================================================
    # EXPERIENCE
    # ============================================================

    experience_years: float = 0.0

    # Broad career level.
    #
    # Examples:
    #   intern
    #   entry
    #   junior
    #   mid
    #   senior
    #
    # This can initially remain empty and be derived from
    # experience when necessary.
    career_level: str = ""

    # ============================================================
    # CAREER INTENT
    # ============================================================

    # Roles the user primarily wants.
    #
    # These represent explicit USER INTENT.
    preferred_roles: list[str] = field(
        default_factory=list
    )

    # Acceptable alternative roles.
    #
    # These should rank below primary roles.
    secondary_roles: list[str] = field(
        default_factory=list
    )

    # Roles inferred from the resume.
    #
    # These represent RESUME EVIDENCE, not user intent.
    resume_roles: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # TECHNICAL PROFILE
    # ============================================================

    skills: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # EDUCATION
    # ============================================================

    education: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # PROJECTS
    # ============================================================

    projects: list[str] = field(
        default_factory=list
    )

    # ============================================================
    # JOB PREFERENCES
    # ============================================================

    preferred_locations: list[str] = field(
        default_factory=list
    )

    minimum_salary_lpa: float = 0.0

    # ============================================================
    # LINKS
    # ============================================================

    github_url: str = ""
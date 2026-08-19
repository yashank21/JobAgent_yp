"""
Job Model

Represents a normalized job collected from any supported source.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Job:

    # -----------------------------
    # Identity
    # -----------------------------

    id: str
    title: str
    company: str

    # -----------------------------
    # Location
    # -----------------------------

    location: str = ""
    remote_type: str = ""

    # -----------------------------
    # Job requirements
    # -----------------------------

    experience_required: str = ""

    # Parsed minimum experience requirement.
    #
    # Example:
    # "2+ years of experience" -> 2.0
    # "1-3 years of experience" -> 1.0
    experience_years_required: float | None = None
    
    seniority: str = "unknown"

    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)

    # -----------------------------
    # Compensation
    # -----------------------------

    salary_min_lpa: float | None = None
    salary_max_lpa: float | None = None

    # -----------------------------
    # Job description
    # -----------------------------

    description: str = ""

    # -----------------------------
    # URLs
    # -----------------------------

    application_url: str = ""
    source_url: str = ""

    # -----------------------------
    # Source
    # -----------------------------

    source: str = ""

    # -----------------------------
    # Dates
    # -----------------------------

    posted_at: datetime | None = None
    fetched_at: datetime | None = None
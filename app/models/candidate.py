from dataclasses import dataclass, field


@dataclass
class CandidateProfile:

    name: str
    email: str
    location: str

    preferred_roles: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)

    minimum_salary_lpa: float = 0.0

    experience_years: float = 0.0

    skills: list[str] = field(default_factory=list)

    education: list[str] = field(default_factory=list)

    projects: list[str] = field(default_factory=list)

    github_url: str | None = None
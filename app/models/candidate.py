"""
Candidate profile model.

Represents a user independently of the ranking system.

Stage 1 refactor: separates resume-derived facts from user preferences
while preserving backward compatibility via __getattr__/__setattr__
delegation.

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
class CandidateFacts:
    """Resume-derived information (not user intent)."""

    skills: list[str] = field(default_factory=list)
    resume_roles: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    career_level: str = ""
    education: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    name: str = ""
    email: str = ""
    github_url: str = ""
    location: str = ""


@dataclass
class CandidatePreferences:
    """User-stated intent and preferences."""

    preferred_roles: list[str] = field(default_factory=list)
    secondary_roles: list[str] = field(default_factory=list)
    preferred_locations: list[str] = field(default_factory=list)
    minimum_salary_lpa: float | None = None
    prefer_remote: bool | None = None


# Fields that belong to CandidateFacts.
_FACT_FIELDS = {f.name for f in CandidateFacts.__dataclass_fields__.values()}

# Fields that belong to CandidatePreferences.
_PREF_FIELDS = {
    f.name for f in CandidatePreferences.__dataclass_fields__.values()
}


class CandidateProfile:
    """Composite profile: facts + preferences with flat-field backward compat."""

    def __init__(self, **kwargs):
        facts_kwargs = {k: v for k, v in kwargs.items() if k in _FACT_FIELDS}
        prefs_kwargs = {k: v for k, v in kwargs.items() if k in _PREF_FIELDS}
        object.__setattr__(self, "facts", CandidateFacts(**facts_kwargs))
        object.__setattr__(
            self, "preferences", CandidatePreferences(**prefs_kwargs)
        )

    def __getattr__(self, name):
        if name in _FACT_FIELDS:
            return getattr(self.facts, name)
        if name in _PREF_FIELDS:
            return getattr(self.preferences, name)
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __setattr__(self, name, value):
        if name in _FACT_FIELDS:
            setattr(self.facts, name, value)
            return
        if name in _PREF_FIELDS:
            setattr(self.preferences, name, value)
            return
        object.__setattr__(self, name, value)

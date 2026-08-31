"""
Default candidate profile configuration.

This file contains ONLY generic defaults.
Candidate-specific information must come from:
    1. uploaded resume
    2. explicit user preferences
"""

from app.models.candidate import CandidateProfile


CANDIDATE_PROFILE = CandidateProfile(
    # Identity is supplied by the application/user.
    name="",
    email="",
    location="",

    # Resume-derived fields are populated by
    # candidate_profile_builder.py.
    experience_years=0.0,
    career_level="",

    # Explicit user intent.
    preferred_roles=[],
    secondary_roles=[],

    # Resume-derived technical profile.
    skills=[],
    resume_roles=[],

    # Resume-derived education/projects.
    education=[],
    projects=[],

    # Explicit user preferences.
    preferred_locations=[],
    minimum_salary_lpa=0.0,

    github_url="",
)
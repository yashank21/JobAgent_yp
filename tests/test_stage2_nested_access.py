"""
Stage 2 regression tests.

Verify that production code reads/writes via the explicit
profile.facts / profile.preferences nested structure.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.services.candidate_profile_builder import build_candidate_profile
from app.scoring.role_scorer import calculate_role_score
from app.scoring.experience_scorer import (
    calculate_experience_score,
)
from app.scoring.job_scorer import (
    calculate_skill_score,
    calculate_role_score as job_calculate_role_score,
    calculate_location_score,
    calculate_salary_score,
)
from app.scoring.final_scorer import calculate_location_score as final_calculate_location_score
from app.scoring.explanation import (
    explain_role_match,
    explain_experience_match,
    explain_salary_match,
    explain_skill_match,
)
from app.eligibility.eligibility import (
    is_experience_eligible,
    is_role_eligible,
    check_eligibility,
)
from run_jobagent import (
    apply_default_preferences,
    collect_explicit_preferences,
)


# ============================================================
# Resume builder writes facts, not preferences
# ============================================================


def test_builder_writes_facts_not_preferences():
    """Resume-derived signals must land in profile.facts."""
    resume_text = """
    Backend Engineer with 3 years of experience.
    Skills: Python, Go, PostgreSQL.
    """
    base = CandidateProfile(
        preferred_roles=["AI Engineer"],
        preferred_locations=["Remote"],
    )

    profile = build_candidate_profile(
        resume_text,
        base_profile=base,
    )

    assert profile.facts.skills
    assert profile.facts.resume_roles
    assert profile.facts.experience_years == 3.0
    assert profile.facts.career_level != "unknown"

    # Preferences must NOT be touched by the builder.
    assert profile.preferences.preferred_roles == ["AI Engineer"]
    assert profile.preferences.preferred_locations == ["Remote"]
    assert profile.preferences.secondary_roles == []
    assert profile.preferences.minimum_salary_lpa is None


def test_builder_fresh_profile_has_default_preferences():
    """A fresh build must have default empty preferences."""
    resume_text = """
    Software Engineer.
    Skills: Python.
    """
    profile = build_candidate_profile(resume_text)

    assert profile.facts.skills
    assert profile.preferences.preferred_roles == []
    assert profile.preferences.secondary_roles == []
    assert profile.preferences.preferred_locations == []
    assert profile.preferences.minimum_salary_lpa is None


# ============================================================
# Preference collection writes preferences
# ============================================================


def test_apply_default_preferences_writes_preferences():
    """apply_default_preferences must not copy resume roles to preferences."""
    profile = CandidateProfile(
        resume_roles=["Backend Engineer", "ML Engineer"],
        skills=["Python"],
    )

    result = apply_default_preferences(profile)

    assert result.preferences.preferred_roles == []
    assert result.facts.resume_roles == [
        "Backend Engineer",
        "ML Engineer",
    ]
    assert result is profile


def test_apply_default_preserves_facts():
    """apply_default_preferences must not modify facts."""
    profile = CandidateProfile(
        resume_roles=["AI Engineer"],
        skills=["Python", "PyTorch"],
        experience_years=2.0,
    )

    apply_default_preferences(profile)

    assert profile.facts.resume_roles == ["AI Engineer"]
    assert profile.facts.skills == ["Python", "PyTorch"]
    assert profile.facts.experience_years == 2.0


# ============================================================
# Role scorer uses explicit sources
# ============================================================


def test_role_scorer_uses_preferences_for_preferred():
    """preferred_roles must come from profile.preferences."""
    candidate = CandidateProfile(
        preferred_roles=["Frontend Engineer"],
        resume_roles=["Backend Engineer"],
    )
    job = Job(
        id="1",
        title="Frontend Engineer",
        company="Test",
        location="Remote",
    )

    score = calculate_role_score(candidate, job)
    assert score == 100.0


def test_role_scorer_uses_preferences_for_secondary():
    """secondary_roles must come from profile.preferences."""
    candidate = CandidateProfile(
        secondary_roles=["Frontend Engineer"],
        resume_roles=["Backend Engineer"],
    )
    job = Job(
        id="1",
        title="Frontend Engineer",
        company="Test",
        location="Remote",
    )

    score = calculate_role_score(candidate, job)
    assert score == 85.0


def test_role_scorer_uses_facts_for_resume_roles():
    """resume_roles must come from profile.facts."""
    candidate = CandidateProfile(
        resume_roles=["Backend Engineer"],
    )
    job = Job(
        id="1",
        title="Backend Engineer",
        company="Test",
        location="Remote",
    )

    score = calculate_role_score(candidate, job)
    assert score == 70.0


# ============================================================
# Experience scorer uses facts
# ============================================================


def test_experience_scorer_uses_facts():
    """experience_years must come from profile.facts."""
    candidate = CandidateProfile(
        experience_years=5.0,
    )
    job = Job(
        id="1",
        title="Senior Engineer",
        company="Test",
        location="Remote",
        experience_years_required=3,
    )

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# Skill scorer uses facts
# ============================================================


def test_skill_scorer_uses_facts():
    """skills must come from profile.facts."""
    candidate = CandidateProfile(
        skills=["Python", "Go"],
    )
    job = Job(
        id="1",
        title="Engineer",
        company="Test",
        location="Remote",
        required_skills=["python"],
    )

    score = calculate_skill_score(candidate, job)
    assert score == 70.0


# ============================================================
# Eligibility reads from facts/preferences
# ============================================================


def test_experience_eligibility_uses_facts():
    """experience_years eligibility check reads from facts."""
    candidate = CandidateProfile(
        experience_years=2.0,
    )
    job = Job(
        id="1",
        title="Engineer",
        company="Test",
        experience_years_required=2,
    )

    assert is_experience_eligible(candidate, job) is True


def test_role_eligibility_uses_preferences():
    """preferred_roles eligibility check reads from preferences."""
    candidate = CandidateProfile(
        preferred_roles=["Software Engineer"],
    )
    job = Job(
        id="1",
        title="Software Engineer",
        company="Test",
        location="Remote",
    )

    assert is_role_eligible(candidate, job) is True

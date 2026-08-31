from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_scorer import calculate_role_score


def make_candidate(
    preferred_roles=None,
    secondary_roles=None,
    resume_roles=None,
    career_level="unknown",
):
    return CandidateProfile(
        name="Test User",
        email="test@example.com",
        location="",
        experience_years=1.0,
        career_level=career_level,
        preferred_roles=preferred_roles or [],
        secondary_roles=secondary_roles or [],
        resume_roles=resume_roles or [],
        skills=["Python"],
        education=[],
        projects=[],
        preferred_locations=[],
        minimum_salary_lpa=0.0,
        github_url="",
    )


def make_job(
    title,
    seniority="unknown",
):
    return Job(
        id="test_job_1",
        title=title,
        company="Test Company",
        location="Remote",
        remote_type="",
        experience_required="",
        description="",
        required_skills=[],
        preferred_skills=[],
        seniority=seniority,
        role_family="",
        ai_confidence=0.0,
    )


def test_exact_preferred_role_match():
    candidate = make_candidate(
        preferred_roles=["Frontend Engineer"]
    )

    job = make_job("Frontend Engineer")

    assert calculate_role_score(candidate, job) == 100.0


def test_secondary_role_match_is_weaker_than_preferred():
    primary = make_candidate(
        preferred_roles=["Frontend Engineer"]
    )

    secondary = make_candidate(
        preferred_roles=["Backend Engineer"],
        secondary_roles=["Frontend Engineer"],
    )

    job = make_job("Frontend Engineer")

    primary_score = calculate_role_score(primary, job)
    secondary_score = calculate_role_score(secondary, job)

    assert primary_score > secondary_score
    assert secondary_score == 85.0


def test_resume_role_can_match():
    candidate = make_candidate(
        resume_roles=["Backend Engineer"]
    )

    job = make_job("Backend Engineer")

    assert calculate_role_score(candidate, job) == 70.0


def test_preferred_role_has_priority_over_resume_role():
    candidate = make_candidate(
        preferred_roles=["Frontend Engineer"],
        resume_roles=["Backend Engineer"],
    )

    job = make_job("Frontend Engineer")

    assert calculate_role_score(candidate, job) == 100.0


def test_secondary_role_has_priority_over_resume_evidence():
    candidate = make_candidate(
        secondary_roles=["Frontend Engineer"],
        resume_roles=["Backend Engineer"],
    )

    job = make_job("Frontend Engineer")

    assert calculate_role_score(candidate, job) == 85.0


def test_unrelated_role_does_not_match():
    candidate = make_candidate(
        preferred_roles=["Frontend Engineer"]
    )

    job = make_job("Data Scientist")

    assert calculate_role_score(candidate, job) == 0.0


def test_unknown_job_role_returns_zero():
    candidate = make_candidate(
        preferred_roles=["Software Engineer"]
    )

    job = make_job("Something Completely Unknown")

    assert calculate_role_score(candidate, job) == 0.0


def test_no_candidate_role_information_returns_zero():
    candidate = make_candidate()

    job = make_job("Software Engineer")

    assert calculate_role_score(candidate, job) == 0.0


def test_same_family_roles_match():
    candidate = make_candidate(
        preferred_roles=["Software Engineer"]
    )

    job = make_job("Backend Engineer")

    assert calculate_role_score(candidate, job) == 100.0


def test_seniority_adjusts_role_score():
    candidate = make_candidate(
        preferred_roles=["Software Engineer"],
        career_level="junior",
    )

    job = make_job(
        "Software Engineer",
        seniority="senior",
    )

    score = calculate_role_score(candidate, job)

    assert score == 92.5


def test_unknown_seniority_does_not_modify_role_score():
    candidate = make_candidate(
        preferred_roles=["Software Engineer"],
        career_level="unknown",
    )

    job = make_job(
        "Software Engineer",
        seniority="unknown",
    )

    assert calculate_role_score(candidate, job) == 100.0


def test_role_matching_is_case_insensitive():
    candidate = make_candidate(
        preferred_roles=["frontend engineer"]
    )

    job = make_job("Frontend Engineer")

    assert calculate_role_score(candidate, job) == 100.0


def test_multiple_preferred_roles_use_best_match():
    candidate = make_candidate(
        preferred_roles=[
            "Data Scientist",
            "Backend Engineer",
        ]
    )

    job = make_job("Backend Engineer")

    assert calculate_role_score(candidate, job) == 100.0


def test_empty_role_values_are_ignored():
    candidate = make_candidate(
        preferred_roles=["", "Backend Engineer", ""]
    )

    job = make_job("Backend Engineer")

    assert calculate_role_score(candidate, job) == 100.0


def test_seniority_one_level_difference():
    candidate = make_candidate(
        preferred_roles=["Software Engineer"],
        career_level="junior",
    )

    job = make_job(
        "Software Engineer",
        seniority="mid",
    )

    score = calculate_role_score(candidate, job)

    assert score == 95.0
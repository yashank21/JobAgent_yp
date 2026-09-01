from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.scoring.explanation import (
    explain_skill_match,
    explain_role_match,
    explain_location_match,
    explain_experience_match,
    explain_salary_match,
    explain_match,
)


def make_candidate(**overrides):
    data = {
        "name": "Yashank",
        "email": "test@example.com",
        "location": "India",
        "preferred_roles": [
            "Software Engineer",
        ],
        "preferred_locations": [
            "India",
            "Remote",
        ],
        "minimum_salary_lpa": 10.0,
        "experience_years": 0.92,
        "skills": [
            "Python",
            "C++",
            "SQL",
            "FastAPI",
        ],
    }

    data.update(overrides)

    return CandidateProfile(**data)


def make_job(
    title="Software Engineer",
    company="Test Company",
    location="India",
    remote_type="",
    experience_required="",
    experience_years_required=None,
    required_skills=None,
    preferred_skills=None,
    salary_min_lpa=None,
    salary_max_lpa=None,
    description="",
    application_url="",
    source_url="",
    source="",
    posted_at=None,
    fetched_at=None,
):
    return Job(
        id="test_job_1",
        title=title,
        company=company,
        location=location,
        remote_type=remote_type,
        experience_required=experience_required,
        experience_years_required=experience_years_required,
        required_skills=(
            required_skills
            if required_skills is not None
            else ["Python", "C++"]
        ),
        preferred_skills=(
            preferred_skills
            if preferred_skills is not None
            else ["FastAPI"]
        ),
        salary_min_lpa=salary_min_lpa,
        salary_max_lpa=salary_max_lpa,
        description=description,
        application_url=application_url,
        source_url=source_url,
        source=source,
        posted_at=posted_at,
        fetched_at=fetched_at,
    )


def test_required_skill_match():

    result = explain_skill_match(
        make_candidate(),
        make_job(),
    )

    assert "✓ Python — required" in result
    assert "✓ C++ — required" in result


def test_missing_required_skill():

    result = explain_skill_match(
        make_candidate(
            skills=["Python"],
        ),
        make_job(),
    )

    assert "✓ Python — required" in result
    assert "✗ C++ — required skill missing" in result


def test_preferred_skill_match():

    result = explain_skill_match(
        make_candidate(),
        make_job(),
    )

    assert "✓ FastAPI — preferred" in result


def test_role_match():

    result = explain_role_match(
        make_candidate(),
        make_job(),
    )

    assert "Role matches preferred role" in result


def test_role_mismatch():

    result = explain_role_match(
        make_candidate(),
        make_job(
            title="Mechanical Engineer",
        ),
    )

    assert "does not match preferred roles" in result


def test_location_match():

    result = explain_location_match(
        make_candidate(),
        make_job(
            location="India",
        ),
    )

    assert "Location matches preference" in result


def test_remote_location_match():

    result = explain_location_match(
        make_candidate(),
        make_job(
            location="Remote",
        ),
    )

    assert "Remote job" in result


def test_location_mismatch():

    result = explain_location_match(
        make_candidate(),
        make_job(
            location="Hawthorne, CA",
        ),
    )

    assert "outside preferred locations" in result


def test_experience_requirement_met():

    result = explain_experience_match(
        make_candidate(
            experience_years=3,
        ),
        make_job(
            experience_years_required=2,
        ),
    )

    assert "Experience requirement met" in result


def test_experience_requirement_not_met():

    result = explain_experience_match(
        make_candidate(
            experience_years=1,
        ),
        make_job(
            experience_years_required=3,
        ),
    )

    assert "Experience requirement not met" in result


def test_salary_meets_requirement():

    result = explain_salary_match(
        make_candidate(
            minimum_salary_lpa=10,
        ),
        make_job(
            salary_max_lpa=15,
        ),
    )

    assert "Salary meets minimum requirement" in result


def test_salary_unavailable():

    result = explain_salary_match(
        make_candidate(
            minimum_salary_lpa=10,
        ),
        make_job(),
    )

    assert "Salary information unavailable" in result


def test_complete_explanation():

    result = explain_match(
        make_candidate(),
        make_job(),
    )

    assert len(result) >= 5
    assert any("required" in item for item in result)
    assert any("Role" in item for item in result)
    assert any("Location" in item for item in result)
    assert any("Experience" in item for item in result)
    assert any("Salary" in item for item in result)


def test_role_explanation_matches_role_family():

    candidate = make_candidate()

    job = make_job(
        title="New Graduate Engineer, Software - '26/'27 (Starlink)"
    )

    result = explain_role_match(
        candidate,
        job,
    )

    assert result == (
        "✓ Role matches preferred role: "
        "Software Engineer"
    )


def test_role_explanation_matches_software_development_engineer():

    candidate = make_candidate()

    job = make_job(
        title="Software Development Engineer"
    )

    result = explain_role_match(
        candidate,
        job,
    )

    assert result == (
        "✓ Role matches preferred role: "
        "Software Engineer"
    )


# ============================================================
# STAGE 6 — EXPLANATION LAYER TESTS
# ============================================================


def test_unset_location_preference_explanation():

    candidate = make_candidate(
        preferred_locations=[],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    result = explain_location_match(candidate, job)

    assert "not configured" in result.lower()
    assert "100%" not in result
    assert "match" not in result.lower() or "not configured" in result.lower()


def test_unset_role_preference_explanation():

    candidate = make_candidate(
        preferred_roles=[],
        secondary_roles=[],
    )

    job = make_job(
        title="Software Engineer",
    )

    result = explain_role_match(candidate, job)

    assert "not configured" in result.lower()


def test_unset_salary_preference_explanation():

    candidate = make_candidate(
        minimum_salary_lpa=None,
    )

    job = make_job(
        salary_max_lpa=15.0,
    )

    result = explain_salary_match(candidate, job)

    assert "not configured" in result.lower()


def test_zero_score_is_not_treated_as_unset():

    candidate = make_candidate(
        preferred_roles=["Software Engineer"],
    )

    job = make_job(
        title="Software Engineer",
    )

    role_result = explain_role_match(candidate, job)

    assert "✓" in role_result
    assert "not configured" not in role_result.lower()


def test_resume_roles_are_explained_as_evidence():

    candidate = CandidateProfile(
        name="Test",
        email="test@example.com",
        resume_roles=["Data Analyst"],
        preferred_roles=[],
        secondary_roles=[],
    )

    job = make_job(
        title="Data Analyst",
    )

    result = explain_role_match(candidate, job)

    assert "resume" in result.lower() or "evidence" in result.lower()


def test_nested_candidate_access_in_explanation():

    candidate = CandidateProfile(
        name="Test",
        email="test@example.com",
        resume_roles=["Backend Engineer"],
        preferred_roles=["Software Engineer"],
        secondary_roles=["Backend Engineer"],
        preferred_locations=["India"],
        minimum_salary_lpa=15.0,
        skills=["Python", "Go"],
    )

    job = make_job(
        title="Software Engineer",
        location="India",
        required_skills=["Python"],
        salary_max_lpa=20.0,
    )

    skill_result = explain_skill_match(candidate, job)
    role_result = explain_role_match(candidate, job)
    location_result = explain_location_match(candidate, job)
    salary_result = explain_salary_match(candidate, job)

    assert "✓ Python — required" in skill_result
    assert "✓" in role_result
    assert "✓" in location_result
    assert "✓" in salary_result


def test_none_scores_do_not_crash():

    candidate = make_candidate(
        preferred_locations=[],
        preferred_roles=[],
        secondary_roles=[],
        minimum_salary_lpa=None,
    )

    job = make_job(
        location="Hawthorne, CA",
        title="Product Manager",
        salary_max_lpa=None,
    )

    result = explain_match(candidate, job)

    assert len(result) >= 5
    assert any("not configured" in r.lower() for r in result)
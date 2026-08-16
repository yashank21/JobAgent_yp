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
from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.eligibility.eligibility import (
    check_eligibility,
    has_work_authorization_restriction,
    is_job_eligible,
)
from app.services.eligibility import (
    is_experience_eligible,
    is_location_eligible,
)


def make_candidate(**kwargs):
    defaults = {
        "name": "Yashank",
        "email": "test@example.com",
        "location": "India",
        "experience_years": 0.92,
        "preferred_roles": [
            "Software Engineer",
        ],
        "preferred_locations": [
            "India",
        ],
    }

    defaults.update(kwargs)

    return CandidateProfile(**defaults)


def make_job(**kwargs):
    defaults = {
        "id": "1",
        "title": "Software Engineer",
        "company": "Example",
        "location": "Bengaluru, India",
    }

    defaults.update(kwargs)

    return Job(**defaults)


# ============================================================
# LOCATION
# ============================================================


def test_matching_location_is_eligible():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Bengaluru, India",
    )

    assert is_location_eligible(
        candidate,
        job,
    )


def test_non_matching_location_is_not_eligible():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    assert not is_location_eligible(
        candidate,
        job,
    )


def test_remote_job_is_eligible():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Remote",
    )

    assert is_location_eligible(
        candidate,
        job,
    )


def test_no_location_preference_allows_job():

    candidate = make_candidate(
        preferred_locations=[],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    assert is_location_eligible(
        candidate,
        job,
    )


# ============================================================
# EXPERIENCE
# ============================================================


def test_sufficient_experience_is_eligible():

    candidate = make_candidate(
        experience_years=2,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert is_experience_eligible(
        candidate,
        job,
    )


def test_insufficient_experience_is_not_eligible():

    candidate = make_candidate(
        experience_years=0.92,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert not is_experience_eligible(
        candidate,
        job,
    )


def test_missing_experience_requirement_is_eligible():

    candidate = make_candidate(
        experience_years=0,
    )

    job = make_job()

    assert is_experience_eligible(
        candidate,
        job,
    )


# ============================================================
# WORK AUTHORIZATION
# ============================================================


def test_itar_restriction_detected():

    job = make_job(
        description=(
            "This position requires compliance "
            "with ITAR regulations."
        ),
    )

    assert has_work_authorization_restriction(
        job,
    )


def test_us_citizenship_restriction_detected():

    job = make_job(
        description=(
            "Applicants must be U.S. citizens "
            "or lawful permanent residents."
        ),
    )

    assert has_work_authorization_restriction(
        job,
    )


def test_normal_job_has_no_detected_restriction():

    job = make_job(
        description=(
            "We are looking for a Python "
            "software engineer."
        ),
    )

    assert not has_work_authorization_restriction(
        job,
    )


# ============================================================
# COMPLETE ELIGIBILITY
# ============================================================


def test_complete_eligible_job():

    candidate = make_candidate(
        preferred_locations=["India"],
        experience_years=2,
    )

    job = make_job(
        location="Bengaluru, India",
        experience_years_required=2,
    )

    result = is_job_eligible(
        candidate,
        job,
    )

    assert result.eligible is True
    assert result.reasons == []


def test_complete_ineligible_job():

    candidate = make_candidate(
        preferred_locations=["India"],
        experience_years=0.5,
    )

    job = make_job(
        location="Hawthorne, CA",
        experience_years_required=2,
    )

    result = is_job_eligible(
        candidate,
        job,
    )

    assert result.eligible is False
    assert len(result.reasons) == 2


# ============================================================
# RESULT / REASONS
# ============================================================


def test_eligible_job_has_no_reasons():

    candidate = make_candidate()

    job = make_job()

    result = check_eligibility(
        candidate,
        job,
    )

    assert result.eligible is True
    assert result.reasons == []


def test_experience_failure_has_reason():

    candidate = make_candidate(
        experience_years=1,
    )

    job = make_job(
        experience_years_required=2,
    )

    result = check_eligibility(
        candidate,
        job,
    )

    assert result.eligible is True
    assert len(result.reasons) == 1
    assert "2+ years" in result.reasons[0]


def test_location_failure_has_reason():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    result = check_eligibility(
        candidate,
        job,
    )

    assert result.eligible is False
    assert len(result.reasons) == 1
    assert "outside preferred locations" in result.reasons[0]


def test_multiple_failures_return_multiple_reasons():

    candidate = make_candidate(
        experience_years=1,
        preferred_locations=["India"],
    )

    job = make_job(
        location="Hawthorne, CA",
        experience_years_required=3,
    )

    result = check_eligibility(
        candidate,
        job,
    )

    assert result.eligible is False
    assert len(result.reasons) == 2


# ============================================================
# ROLE FAMILY
# ============================================================


def test_software_engineer_role_is_eligible():

    result = is_job_eligible(
        make_candidate(),
        make_job(
            title="Software Engineer",
        ),
    )

    assert result.eligible is True
    assert result.reasons == []


def test_software_development_engineer_role_is_eligible():

    result = is_job_eligible(
        make_candidate(),
        make_job(
            title="Software Development Engineer",
        ),
    )

    assert result.eligible is True
    assert result.reasons == []


def test_new_grad_software_role_is_eligible():

    result = is_job_eligible(
        make_candidate(),
        make_job(
            title=(
                "New Graduate Engineer, "
                "Software - '26/'27 (Starlink)"
            ),
        ),
    )

    assert result.eligible is True
    assert result.reasons == []


def test_unrelated_role_is_not_eligible():

    result = is_job_eligible(
        make_candidate(),
        make_job(
            title="Food Services Specialist - Restaurants",
        ),
    )

    assert result.eligible is False
    assert any(
        "does not match preferred roles"
        in reason
        for reason in result.reasons
    )


def test_production_scheduler_is_not_eligible():

    result = is_job_eligible(
        make_candidate(),
        make_job(
            title="Production Control Scheduler (Falcon)",
        ),
    )

    assert result.eligible is False
    assert any(
        "does not match preferred roles"
        in reason
        for reason in result.reasons
    )


# ============================================================
# STAGE 5 — ELIGIBILITY SEMANTICS
# ============================================================


def test_unset_location_preference_is_eligible():

    candidate = make_candidate(
        preferred_locations=[],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    result = is_job_eligible(candidate, job)

    assert result.eligible is True
    assert not any(
        "outside preferred locations" in r
        for r in result.reasons
    )


def test_configured_location_preference_is_enforced():

    candidate = make_candidate(
        preferred_locations=["Bengaluru"],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    result = is_job_eligible(candidate, job)

    assert result.eligible is False
    assert any(
        "outside preferred locations" in r
        for r in result.reasons
    )


def test_unset_role_preference_is_eligible():

    candidate = make_candidate(
        preferred_roles=[],
        secondary_roles=[],
    )

    job = make_job(
        title="Product Manager",
    )

    result = is_job_eligible(candidate, job)

    assert result.eligible is True
    assert not any(
        "does not match preferred roles" in r
        for r in result.reasons
    )


def test_configured_role_preference_is_enforced():

    candidate = make_candidate(
        preferred_roles=["Software Engineer"],
        secondary_roles=[],
    )

    job = make_job(
        title="Product Manager",
    )

    result = is_job_eligible(candidate, job)

    assert result.eligible is False
    assert any(
        "does not match preferred roles" in r
        for r in result.reasons
    )


def test_unset_salary_preference_does_not_reject():

    candidate = make_candidate(
        minimum_salary_lpa=None,
    )

    job = make_job(
        salary_min_lpa=None,
        salary_max_lpa=None,
    )

    result = check_eligibility(candidate, job)

    assert result.eligible is True
    assert not any(
        "salary" in r.lower()
        for r in result.reasons
    )


def test_explicit_salary_preference_preserves_existing_behavior():

    candidate = make_candidate(
        minimum_salary_lpa=10.0,
    )

    job = make_job(
        salary_min_lpa=5.0,
        salary_max_lpa=8.0,
    )

    result = check_eligibility(candidate, job)

    assert result.eligible is True


def test_unset_remote_preference_does_not_reject():

    candidate = make_candidate(
        prefer_remote=None,
    )

    job = make_job(
        location="Bengaluru, India",
        remote_type="",
    )

    result = check_eligibility(candidate, job)

    assert result.eligible is True
    assert not any(
        "remote" in r.lower()
        for r in result.reasons
    )


def test_resume_roles_are_not_hard_role_preferences():

    candidate = CandidateProfile(
        name="Test",
        email="test@example.com",
        resume_roles=["Software Engineer"],
        preferred_roles=[],
        secondary_roles=[],
    )

    job = make_job(
        title="Product Manager",
    )

    result = is_job_eligible(candidate, job)

    assert result.eligible is True
    assert not any(
        "does not match preferred roles" in r
        for r in result.reasons
    )


def test_preferences_survive_resume_facts():

    candidate = CandidateProfile(
        name="Test",
        email="test@example.com",
        resume_roles=["Data Analyst"],
        preferred_roles=["Software Engineer"],
        secondary_roles=["Backend Engineer"],
        preferred_locations=["India"],
        minimum_salary_lpa=15.0,
        prefer_remote=True,
    )

    assert candidate.preferences.preferred_roles == [
        "Software Engineer",
    ]
    assert candidate.preferences.secondary_roles == [
        "Backend Engineer",
    ]
    assert candidate.preferences.preferred_locations == [
        "India",
    ]
    assert candidate.preferences.minimum_salary_lpa == 15.0
    assert candidate.preferences.prefer_remote is True

    assert candidate.facts.resume_roles == [
        "Data Analyst",
    ]
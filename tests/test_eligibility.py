from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.services.eligibility import (
    has_work_authorization_restriction,
    is_experience_eligible,
    is_job_eligible,
    is_location_eligible,
)


def make_candidate(**kwargs):
    defaults = {
        "name": "Yashank",
        "email": "test@example.com",
        "location": "India",
        "experience_years": 0.92,
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


def test_sufficient_experience_is_eligible():

    candidate = make_candidate(
        experience_years=2,
    )

    job = make_job()

    job.experience_years_required = 2

    assert is_experience_eligible(
        candidate,
        job,
    )


def test_insufficient_experience_is_not_eligible():

    candidate = make_candidate(
        experience_years=0.92,
    )

    job = make_job()

    job.experience_years_required = 2

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


def test_complete_eligible_job():

    candidate = make_candidate(
        preferred_locations=["India"],
        experience_years=2,
    )

    job = make_job(
        location="Bengaluru, India",
    )

    job.experience_years_required = 2

    assert is_job_eligible(
        candidate,
        job,
    )


def test_complete_ineligible_job():

    candidate = make_candidate(
        preferred_locations=["India"],
        experience_years=0.5,
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    job.experience_years_required = 2

    assert not is_job_eligible(
        candidate,
        job,
    )

from app.eligibility.eligibility import (
    check_eligibility,
)
from app.models.candidate import CandidateProfile
from app.models.job import Job


def make_candidate(**kwargs):
    defaults = {
        "name": "Yashank",
        "email": "test@example.com",
        "location": "India",
        "experience_years": 1.0,
        "preferred_locations": ["India"],
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

    assert result.eligible is False
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


def test_remote_job_is_eligible():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Remote",
    )

    result = check_eligibility(
        candidate,
        job,
    )

    assert result.eligible is True
    assert result.reasons == []
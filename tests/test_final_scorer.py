from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.scoring.experience_scorer import calculate_experience_score
from app.scoring.final_scorer import (
    calculate_final_score,
    calculate_location_score,
    rank_jobs,
    score_job,
)


def make_candidate(**kwargs):
    defaults = {
        "name": "Test User",
        "email": "test@example.com",
        "location": "India",
        "experience_years": 1.0,
        "skills": [
            "Python",
            "C++",
            "FastAPI",
        ],
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
        "required_skills": [
            "python",
            "c++",
        ],
        "preferred_skills": [
            "fastapi",
        ],
    }

    defaults.update(kwargs)

    return Job(**defaults)


# ============================================================
# Experience scoring
# ============================================================


def test_experience_score_no_requirement():

    candidate = make_candidate(
        experience_years=0,
    )

    job = make_job()

    assert calculate_experience_score(
        candidate,
        job,
    ) == 100.0


def test_experience_score_meets_requirement():

    candidate = make_candidate(
        experience_years=2,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 100.0


def test_experience_score_exceeds_requirement():

    candidate = make_candidate(
        experience_years=4,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 100.0


def test_experience_score_partial_match():

    candidate = make_candidate(
        experience_years=1,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 50.0


def test_experience_score_zero_candidate_experience():

    candidate = make_candidate(
        experience_years=0,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 0.0


# ============================================================
# Location scoring
# ============================================================


def test_location_score_matching_location():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Bengaluru, India",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) == 100.0


def test_location_score_non_matching_location():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) == 0.0


def test_location_score_remote():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Remote",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) == 100.0


def test_location_score_no_preference():

    candidate = make_candidate(
        preferred_locations=[],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) is None


# ============================================================
# Final score
# ============================================================


def test_final_score_perfect_match():

    score = calculate_final_score(
        skill_score=100,
        role_score=100,
        experience_score=100,
        location_score=100,
    )

    assert score == 100.0


def test_final_score_zero():

    score = calculate_final_score(
        skill_score=0,
        role_score=0,
        experience_score=0,
        location_score=0,
    )

    assert score == 0.0




# ============================================================
# Role mismatch caps
# ============================================================








# ============================================================
# Experience mismatch caps
# ============================================================








# ============================================================
# Individual job scoring
# ============================================================


def test_score_job_returns_match():

    candidate = make_candidate(
        experience_years=2,
    )

    job = make_job(
    experience_required="2+ years of experience",
)

    match = score_job(
        candidate,
        job,
    )

    assert match.job == job
    assert match.eligible is True
    assert match.skill_score > 0
    assert match.role_score > 0
    assert match.experience_score == 100.0
    assert match.location_score == 100.0
    assert match.final_score > 0
    assert match.eligibility_reasons == []


def test_score_job_contains_eligibility_reasons():

    candidate = make_candidate(
        experience_years=1,
        preferred_locations=["India"],
    )

    job = make_job(
        location="Hawthorne, CA",
        experience_years_required=3,
    )

    match = score_job(
        candidate,
        job,
    )

    assert match.eligible is False

    assert len(match.eligibility_reasons) == 2

    assert any(
        "3+ years" in reason
        for reason in match.eligibility_reasons
    )

    assert any(
        "outside preferred locations" in reason
        for reason in match.eligibility_reasons
    )


# ============================================================
# Ranking
# ============================================================


def test_ineligible_jobs_are_excluded():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    eligible_job = make_job(
        id="1",
        location="Bengaluru, India",
    )

    ineligible_job = make_job(
        id="2",
        location="Hawthorne, CA",
    )

    results = rank_jobs(
        candidate,
        [
            ineligible_job,
            eligible_job,
        ],
    )

    assert len(results) == 1
    assert results[0].job.id == "1"


def test_jobs_are_ranked_by_final_score():

    candidate = make_candidate()

    strong_job = make_job(
        id="strong",
        required_skills=[
            "python",
            "c++",
        ],
        preferred_skills=[
            "fastapi",
        ],
    )

    weak_job = make_job(
        id="weak",
        required_skills=[
            "java",
        ],
    )

    results = rank_jobs(
        candidate,
        [
            weak_job,
            strong_job,
        ],
    )

    assert len(results) == 2
    assert results[0].job.id == "strong"
    assert results[1].job.id == "weak"
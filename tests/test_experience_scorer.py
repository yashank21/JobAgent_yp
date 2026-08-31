from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.experience_scorer import calculate_experience_score


def make_candidate(experience_years):
    return CandidateProfile(
        name="Yashank",
        email="yashank@example.com",
        location="India",
        experience_years=experience_years,
    )


def make_job(experience_required):
    return Job(
        id="1",
        title="Software Engineer",
        company="Example",
        experience_required=experience_required,
    )


def test_candidate_meets_experience_requirement():

    candidate = make_candidate(2.0)

    job = make_job(
        "2+ years of experience"
    )

    score = calculate_experience_score(
        candidate,
        job,
    )

    assert score == 100.0


def test_candidate_exceeds_experience_requirement():

    candidate = make_candidate(4.0)

    job = make_job(
        "2+ years of experience"
    )

    score = calculate_experience_score(
        candidate,
        job,
    )

    assert score == 100.0


def test_candidate_has_partial_experience():

    candidate = make_candidate(1.0)

    job = make_job(
        "2+ years of experience"
    )

    score = calculate_experience_score(
        candidate,
        job,
    )

    assert score == 50.0


def test_candidate_has_no_experience():

    candidate = make_candidate(0.0)

    job = make_job(
        "2+ years of experience"
    )

    score = calculate_experience_score(
        candidate,
        job,
    )

    assert score == 0.0


def test_job_has_no_experience_requirement():

    candidate = make_candidate(0.0)

    job = make_job("")

    score = calculate_experience_score(
        candidate,
        job,
    )

    assert score == 100.0


def test_internship_experience_is_counted():

    candidate = make_candidate(
        11 / 12
    )

    job = make_job(
        "2+ years of experience"
    )

    score = calculate_experience_score(
        candidate,
        job,
    )

    assert score == round((11 / 12) / 2 * 100, 2)
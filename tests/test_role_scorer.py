from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_scorer import calculate_role_score


def make_candidate(preferred_roles):
    return CandidateProfile(
        name="Test",
        email="test@example.com",
        location="India",
        preferred_roles=preferred_roles,
        preferred_locations=["India", "Remote"],
        minimum_salary_lpa=10.0,
        experience_years=1.0,
        skills=["Python"],
    )


def make_job(title):
    return Job(
        id="test_job_1",
        title=title,
        company="Test Company",
        location="India",
    )


def test_software_engineer_matches_new_grad_software():
    candidate = make_candidate(["Software Engineer"])

    job = make_job(
        "New Graduate Engineer, Software - '26/'27 (Starlink)"
    )

    assert calculate_role_score(candidate, job) == 100.0


def test_software_engineer_matches_software_development_engineer():
    candidate = make_candidate(["Software Engineer"])

    job = make_job(
        "Software Development Engineer"
    )

    assert calculate_role_score(candidate, job) == 100.0


def test_unrelated_role_does_not_match():
    candidate = make_candidate(["Software Engineer"])

    job = make_job(
        "Mechanical Engineer"
    )

    assert calculate_role_score(candidate, job) == 0.0

def test_ai_engineer_matches_ml_engineer_strongly():
    candidate = make_candidate(["AI Engineer"])

    job = make_job("Machine Learning Engineer")

    score = calculate_role_score(candidate, job)

    assert score == 95.0


def test_ai_engineer_matches_llm_engineer_strongly():
    candidate = make_candidate(["AI Engineer"])

    job = make_job("LLM Engineer")

    score = calculate_role_score(candidate, job)

    assert score == 95.0


def test_ai_engineer_matches_forward_deployed_engineer():
    candidate = make_candidate(["AI Engineer"])

    job = make_job("Forward Deployed Engineer")

    score = calculate_role_score(candidate, job)

    assert score == 85.0


def test_ai_engineer_matches_data_scientist():
    candidate = make_candidate(["AI Engineer"])

    job = make_job("Data Scientist")

    score = calculate_role_score(candidate, job)

    assert score == 75.0


def test_ai_engineer_weakly_matches_generic_software_engineer():
    candidate = make_candidate(["AI Engineer"])

    job = make_job("Software Engineer")

    score = calculate_role_score(candidate, job)

    assert score == 40.0


def test_ai_engineer_does_not_match_mechanical_engineer():
    candidate = make_candidate(["AI Engineer"])

    job = make_job("Mechanical Engineer")

    score = calculate_role_score(candidate, job)

    assert score == 0.0
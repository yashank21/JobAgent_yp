from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.match_engine import calculate_match


def test_strong_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        experience_years=3,
        skills=[
            "Python",
            "C++",
            "FastAPI",
            "React",
        ],
    )

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
        experience_required="2+ years of experience",
        required_skills=[
            "python",
            "c++",
        ],
        preferred_skills=[
            "fastapi",
            "react",
        ],
    )

    result = calculate_match(
        candidate,
        job,
    )

    assert result.skill_score == 100.0
    assert result.experience_score == 100.0
    assert result.overall_score == 100.0


def test_partial_experience_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        experience_years=1,
        skills=[
            "Python",
            "C++",
        ],
    )

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
        experience_required="2+ years of experience",
        required_skills=[
            "python",
            "c++",
        ],
    )

    result = calculate_match(
        candidate,
        job,
    )

    assert result.skill_score == 70.0
    assert result.experience_score == 50.0
    assert result.overall_score == 64.0
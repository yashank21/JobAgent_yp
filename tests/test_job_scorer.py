from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.scoring.job_scorer import (
    calculate_skill_score,
)
from app.scoring.role_scorer import (
    calculate_role_score,
)


# ============================================================
# Skill scoring
# ============================================================


def test_all_required_and_preferred_skills_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="yashank@example.com",
        location="India",
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
        required_skills=[
            "python",
            "c++",
        ],
        preferred_skills=[
            "fastapi",
            "react",
        ],
    )

    score = calculate_skill_score(
        candidate,
        job,
    )

    assert score == 100.0


def test_only_required_skills_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="yashank@example.com",
        location="India",
        skills=[
            "Python",
            "C++",
        ],
    )

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
        required_skills=[
            "python",
            "c++",
        ],
        preferred_skills=[
            "fastapi",
            "react",
        ],
    )

    score = calculate_skill_score(
        candidate,
        job,
    )

    assert score == 70.0


def test_partial_required_skills_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="yashank@example.com",
        location="India",
        skills=[
            "Python",
        ],
    )

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
        required_skills=[
            "python",
            "c++",
        ],
    )

    score = calculate_skill_score(
        candidate,
        job,
    )

    assert score == 35.0


def test_no_skills_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="yashank@example.com",
        location="India",
        skills=[
            "Java",
        ],
    )

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
        required_skills=[
            "python",
            "c++",
        ],
    )

    score = calculate_skill_score(
        candidate,
        job,
    )

    assert score == 0.0


def test_no_job_skills():

    candidate = CandidateProfile(
        name="Yashank",
        email="yashank@example.com",
        location="India",
        skills=[
            "Python",
        ],
    )

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
    )

    score = calculate_skill_score(
        candidate,
        job,
    )

    assert score == 50.0


# ============================================================
# Role scoring
# ============================================================


def test_role_score_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        preferred_roles=[
            "Software Engineer",
        ],
    )

    job = Job(
        id="1",
        title="Senior Software Engineer",
        company="Example",
    )

    score = calculate_role_score(
        candidate,
        job,
    )

    assert score == 100.0


def test_role_score_no_match():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        preferred_roles=[
            "Data Engineer",
        ],
    )

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
    )

    score = calculate_role_score(
        candidate,
        job,
    )

    assert score == 75.0
    
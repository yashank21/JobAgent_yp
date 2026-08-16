from app.models.job import Job
from app.models.match import JobMatch


def test_job_match_defaults():

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
    )

    match = JobMatch(job=job)

    assert match.job == job
    assert match.eligible is True
    assert match.eligibility_reasons == []

    assert match.skill_score == 0.0
    assert match.role_score == 0.0
    assert match.experience_score == 0.0
    assert match.location_score == 0.0
    assert match.salary_score == 0.0

    assert match.final_score == 0.0


def test_job_match_with_scores():

    job = Job(
        id="1",
        title="Software Engineer",
        company="Example",
    )

    match = JobMatch(
        job=job,
        eligible=True,
        skill_score=80.0,
        role_score=90.0,
        experience_score=100.0,
        location_score=50.0,
        salary_score=75.0,
        final_score=82.5,
    )

    assert match.skill_score == 80.0
    assert match.role_score == 90.0
    assert match.experience_score == 100.0
    assert match.location_score == 50.0
    assert match.salary_score == 75.0
    assert match.final_score == 82.5


def test_ineligible_job():

    job = Job(
        id="1",
        title="Senior Software Engineer",
        company="Example",
    )

    match = JobMatch(
        job=job,
        eligible=False,
        eligibility_reasons=[
            "Requires 5+ years of experience",
            "Location is not supported",
        ],
    )

    assert match.eligible is False
    assert len(match.eligibility_reasons) == 2
    assert "Requires 5+ years of experience" in match.eligibility_reasons
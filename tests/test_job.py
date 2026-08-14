from datetime import datetime

from app.models.job import Job


def test_job_model():

    job = Job(
        id="test-001",
        title="Software Engineer",
        company="Example Corp",
        location="Bengaluru",
        remote_type="Hybrid",
        experience_required="0-2 years",
        required_skills=["Python", "SQL"],
        preferred_skills=["Docker"],
        salary_min_lpa=8.0,
        salary_max_lpa=12.0,
        description="Backend engineering role.",
        application_url="https://example.com/apply",
        source_url="https://example.com/job",
        source="test",
        posted_at=datetime.now(),
        fetched_at=datetime.now(),
    )

    assert job.id == "test-001"
    assert job.title == "Software Engineer"
    assert job.company == "Example Corp"
    assert "Python" in job.required_skills
    assert job.salary_max_lpa == 12.0
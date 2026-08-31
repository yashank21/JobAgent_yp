from datetime import datetime, timezone

from app.collectors.wellfound import WellfoundCollector


class FakeHTTPClient:

    def __init__(self, response):
        self.response = response
        self.requested_url = None

    def get(self, url):
        self.requested_url = url
        return self.response


def test_parse_wellfound_job():

    fake_http = FakeHTTPClient({})

    collector = WellfoundCollector(
        http_client=fake_http,
    )

    raw_job = {
        "id": 123,
        "title": "AI Engineer",
        "company": "Example AI",
        "location": "Bengaluru, India",
        "remote_type": "Hybrid",
        "experience_required": "1-3 years",
        "experience_years_required": 1.0,
        "required_skills_text": (
            "Python, SQL, PyTorch"
        ),
        "preferred_skills_text": (
            "Docker, AWS"
        ),
        "salary_min_lpa": 8.0,
        "salary_max_lpa": 14.0,
        "description": (
            "<p>Build AI systems using "
            "Python and PyTorch.</p>"
        ),
        "application_url": (
            "https://example.com/jobs/123"
        ),
        "source_url": (
            "https://example.com/jobs/123"
        ),
        "posted_at": (
            "2026-08-17T08:00:00+00:00"
        ),
    }

    job = collector._parse_job(raw_job)

    assert job.id == "123"
    assert job.title == "AI Engineer"
    assert job.company == "Example AI"

    assert job.location == "Bengaluru, India"
    assert job.remote_type == "Hybrid"

    assert job.experience_required == "1-3 years"
    assert job.experience_years_required == 1.0

    assert "python" in job.required_skills
    assert "sql" in job.required_skills
    assert "pytorch" in job.required_skills

    assert "docker" in job.preferred_skills
    assert "aws" in job.preferred_skills

    assert job.salary_min_lpa == 8.0
    assert job.salary_max_lpa == 14.0

    assert job.description == (
        "Build AI systems using "
        "Python and PyTorch."
    )

    assert job.application_url == (
        "https://example.com/jobs/123"
    )

    assert job.source == "wellfound"

    assert job.posted_at == datetime.fromisoformat(
        "2026-08-17T08:00:00+00:00"
    )


def test_parse_wellfound_job_uses_enrichment_when_experience_is_none():
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    job = collector._parse_job({
        "id": 456,
        "title": "AI Engineer",
        "company": "Example AI",
        "description": "3+ years of experience with Python.",
        "experience_years_required": None,
    })

    assert job.experience_years_required == 3.0


def test_parse_wellfound_job_preserves_explicit_experience_value():
    collector = WellfoundCollector(http_client=FakeHTTPClient({}))

    job = collector._parse_job({
        "id": 789,
        "title": "AI Engineer",
        "company": "Example AI",
        "description": "3+ years of experience with Python.",
        "experience_years_required": 2.0,
    })

    assert job.experience_years_required == 2.0


def test_wellfound_urls_follow_user_roles_not_a_hardcoded_ai_path():
    from app.collectors.wellfound import wellfound_search_urls

    urls = wellfound_search_urls(
        roles=["Backend Engineer", "Software Engineer"],
        locations=["India"],
    )

    assert urls == [
        "https://wellfound.com/role/l/backend-engineer/india",
        "https://wellfound.com/role/l/software-engineer/india",
    ]
    assert all("ai-engineer" not in url for url in urls)
    
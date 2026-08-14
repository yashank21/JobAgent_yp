from app.collectors.greenhouse import GreenhouseCollector


def test_greenhouse_collector():

    raw_jobs = [
        {
            "id": 123,
            "title": "Software Engineer",
            "location": "Bengaluru",
            "remote_type": "Hybrid",
            "experience_required": "0-2 years",
            "required_skills": [
                "Python",
                "SQL",
                "Git",
            ],
            "preferred_skills": [
                "Docker",
            ],
            "salary_min_lpa": 8,
            "salary_max_lpa": 12,
            "description": "Build backend services.",
            "application_url": "https://example.com/apply",
            "source_url": "https://example.com/job",
        }
    ]

    collector = GreenhouseCollector(
        company="Example Corp",
        board_token="example",
    )

    jobs = collector.collect(raw_jobs)

    assert len(jobs) == 1

    job = jobs[0]

    assert job.id == "123"
    assert job.title == "Software Engineer"
    assert job.company == "Example Corp"
    assert job.location == "Bengaluru"
    assert "Python" in job.required_skills
    assert job.salary_max_lpa == 12
    assert job.source == "greenhouse"
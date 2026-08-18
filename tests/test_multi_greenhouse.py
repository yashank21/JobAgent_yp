from app.collectors.multi_greenhouse import (
    MultiGreenhouseCollector,
)
from app.models.job import Job


class FakeHTTPClient:
    def __init__(self, responses):
        self.responses = responses
        self.requested_urls = []

    def get(self, url):
        self.requested_urls.append(url)

        for board_token, response in self.responses.items():
            if f"/boards/{board_token}/" in url:
                return response

        raise RuntimeError(
            f"No fake response configured for {url}"
        )


def make_job(
    job_id,
    company,
):
    return Job(
        id=str(job_id),
        title="Software Engineer",
        company=company,
        source="greenhouse",
    )


def test_collects_from_multiple_companies():

    fake_http = FakeHTTPClient(
        {
            "company-a": {
                "jobs": [
                    {
                        "id": 1,
                        "title": "AI Engineer",
                        "location": {
                            "name": "India"
                        },
                        "content": "",
                        "first_published": (
                            "2026-08-17T10:00:00+00:00"
                        ),
                        "absolute_url": (
                            "https://example.com/1"
                        ),
                    }
                ]
            },
            "company-b": {
                "jobs": [
                    {
                        "id": 2,
                        "title": "ML Engineer",
                        "location": {
                            "name": "Remote"
                        },
                        "content": "",
                        "first_published": (
                            "2026-08-17T11:00:00+00:00"
                        ),
                        "absolute_url": (
                            "https://example.com/2"
                        ),
                    }
                ]
            },
        }
    )

    collector = MultiGreenhouseCollector(
        companies=[
            {
                "company": "Company A",
                "board_token": "company-a",
            },
            {
                "company": "Company B",
                "board_token": "company-b",
            },
        ],
        http_client=fake_http,
    )

    jobs = collector.collect()

    assert len(jobs) == 2

    assert jobs[0].company == "Company A"
    assert jobs[1].company == "Company B"


def test_failed_company_does_not_stop_collection():

    fake_http = FakeHTTPClient(
        {
            "working-company": {
                "jobs": [
                    {
                        "id": 1,
                        "title": "AI Engineer",
                        "location": {
                            "name": "India"
                        },
                        "content": "",
                        "first_published": (
                            "2026-08-17T10:00:00+00:00"
                        ),
                        "absolute_url": (
                            "https://example.com/1"
                        ),
                    }
                ]
            }
        }
    )

    collector = MultiGreenhouseCollector(
        companies=[
            {
                "company": "Broken Company",
                "board_token": "broken-company",
            },
            {
                "company": "Working Company",
                "board_token": "working-company",
            },
        ],
        http_client=fake_http,
    )

    jobs = collector.collect()

    assert len(jobs) == 1
    assert jobs[0].company == "Working Company"


def test_duplicate_jobs_are_removed():

    fake_http = FakeHTTPClient(
        {
            "company-a": {
                "jobs": [
                    {
                        "id": 123,
                        "title": "AI Engineer",
                        "location": {
                            "name": "India"
                        },
                        "content": "",
                        "first_published": (
                            "2026-08-17T10:00:00+00:00"
                        ),
                        "absolute_url": (
                            "https://example.com/123"
                        ),
                    }
                ]
            },
        }
    )

    collector = MultiGreenhouseCollector(
        companies=[
            {
                "company": "Company A",
                "board_token": "company-a",
            },
            {
                "company": "Company A Again",
                "board_token": "company-a",
            },
        ],
        http_client=fake_http,
    )

    jobs = collector.collect()

    assert len(jobs) == 1
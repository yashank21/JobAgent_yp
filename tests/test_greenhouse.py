from datetime import datetime

from app.collectors.greenhouse import GreenhouseCollector


class FakeHTTPClient:
    """Fake HTTP client used for testing."""

    def __init__(self, response):
        self.response = response
        self.requested_url = None

    def get(self, url):
        self.requested_url = url
        return self.response


def test_greenhouse_collector():

    fake_response = {
        "jobs": [
            {
                "id": 123,
                "title": "Software Engineer",
                "location": {
                    "name": "Bengaluru"
                },
                "first_published": (
                    "2026-07-21T19:49:28-04:00"
                ),
                "absolute_url": (
                    "https://example.com/jobs/123"
                ),
                "content": (
                    "&lt;div&gt;"
                    "&lt;p&gt;Python &amp; SQL&lt;/p&gt;"
                    "&lt;/div&gt;"
                ),
            }
        ]
    }

    fake_http = FakeHTTPClient(fake_response)

    collector = GreenhouseCollector(
        company="Example Corp",
        board_token="example",
        http_client=fake_http,
    )

    jobs = collector.collect()

    assert len(jobs) == 1

    job = jobs[0]

    assert job.id == "123"
    assert job.title == "Software Engineer"
    assert job.company == "Example Corp"
    assert job.location == "Bengaluru"
    assert job.source == "greenhouse"

    assert job.description == "Python & SQL"

    assert job.posted_at == datetime.fromisoformat(
        "2026-07-21T19:49:28-04:00"
    )

    assert fake_http.requested_url == (
        "https://boards-api.greenhouse.io/v1/boards/"
        "example/jobs?content=true"
    )
"""
Greenhouse Job Collector

Collects and normalizes jobs from a Greenhouse-style API.
"""

from datetime import datetime

from app.collectors.base import BaseCollector
from app.models.job import Job


class GreenhouseCollector(BaseCollector):
    """Collect jobs from a Greenhouse job board."""

    def __init__(self, company: str, board_token: str):
        self.company = company
        self.board_token = board_token

    def collect(self, raw_jobs: list[dict] | None = None) -> list[Job]:
        """
        Convert raw Greenhouse job data into Job objects.

        raw_jobs is temporarily injected for testing.
        Later the collector will fetch this data from the API.
        """

        if raw_jobs is None:
            return []

        return [
            self._parse_job(raw_job)
            for raw_job in raw_jobs
        ]

    def _parse_job(self, raw_job: dict) -> Job:
        """Convert one raw job dictionary into our Job model."""

        return Job(
            id=str(raw_job["id"]),
            title=raw_job["title"],
            company=self.company,
            location=raw_job.get("location", ""),
            remote_type=raw_job.get("remote_type", ""),
            experience_required=raw_job.get(
                "experience_required",
                "",
            ),
            required_skills=raw_job.get(
                "required_skills",
                [],
            ),
            preferred_skills=raw_job.get(
                "preferred_skills",
                [],
            ),
            salary_min_lpa=raw_job.get(
                "salary_min_lpa",
            ),
            salary_max_lpa=raw_job.get(
                "salary_max_lpa",
            ),
            description=raw_job.get(
                "description",
                "",
            ),
            application_url=raw_job.get(
                "application_url",
                "",
            ),
            source_url=raw_job.get(
                "source_url",
                "",
            ),
            source="greenhouse",
        )
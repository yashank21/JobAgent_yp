"""
Greenhouse Job Collector

Collects and normalizes jobs from a Greenhouse-style API.
"""

from app.collectors.base import BaseCollector
from app.models.job import Job
from app.services.http_client import HTTPClient
from app.services.text_cleaner import clean_html
from app.services.date_parser import parse_greenhouse_date
from app.services.job_parser import extract_section
from app.services.skill_extractor import extract_skills


class GreenhouseCollector(BaseCollector):
    """Collect jobs from a Greenhouse job board."""

    def __init__(
        self,
        company: str,
        board_token: str,
        http_client: HTTPClient,
    ):
        self.company = company
        self.board_token = board_token
        self.http_client = http_client

    def collect(self) -> list[Job]:
        """
        Fetch jobs from Greenhouse and convert them
        into Job objects.
        """

        url = (
            "https://boards-api.greenhouse.io/v1/boards/"
            f"{self.board_token}/jobs?content=true"
        )

        response = self.http_client.get(url)

        raw_jobs = response.get("jobs", [])

        return [
            self._parse_job(raw_job)
            for raw_job in raw_jobs
        ]

    def _parse_job(self, raw_job: dict) -> Job:
        """Convert one Greenhouse job into our Job model."""

        # ----------------------------------------
        # Location
        # ----------------------------------------

        location = raw_job.get("location", "")

        if isinstance(location, dict):
            location = location.get("name", "")

        # ----------------------------------------
        # Description
        # ----------------------------------------

        description = clean_html(
            raw_job.get("content", "")
        )

        # ----------------------------------------
        # Job sections
        # ----------------------------------------

        basic_qualifications = extract_section(
            description,
            "BASIC QUALIFICATIONS",
            [
                "PREFERRED SKILLS",
                "ADDITIONAL REQUIREMENTS",
                "COMPENSATION AND BENEFITS",
                "ITAR REQUIREMENTS",
            ],
        )

        preferred_skills_text = extract_section(
            description,
            "PREFERRED SKILLS",
            [
                "ADDITIONAL REQUIREMENTS",
                "COMPENSATION AND BENEFITS",
                "ITAR REQUIREMENTS",
            ],
        )

        # ----------------------------------------
        # Skills
        # ----------------------------------------

        required_skills = extract_skills(
            basic_qualifications
        )

        preferred_skills = extract_skills(
            preferred_skills_text
        )

        # ----------------------------------------
        # Job object
        # ----------------------------------------

        return Job(
            id=str(raw_job["id"]),
            title=raw_job.get("title", ""),
            company=raw_job.get(
                "company_name",
                self.company,
            ),
            location=location,
            description=description,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            application_url=raw_job.get(
                "absolute_url",
                "",
            ),
            source_url=raw_job.get(
                "absolute_url",
                "",
            ),
            source="greenhouse",
            posted_at=parse_greenhouse_date(
                raw_job.get(
                    "first_published",
                    "",
                )
            ),
        )
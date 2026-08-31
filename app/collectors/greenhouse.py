"""
Greenhouse Job Collector

Collects and normalizes jobs from a Greenhouse-style API.
"""

from app.collectors.base import BaseCollector
from app.models.job import Job
from app.services.http_client import HTTPClient
from app.services.date_parser import parse_greenhouse_date
from app.services.job_enrichment import enrich_job_description


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

        raw_description = (
            raw_job.get("content", "")
        )

        title = raw_job.get(
            "title",
            "",
        )

        enrichment = enrich_job_description(
            raw_description,
            title=title,
        )

        # ----------------------------------------
        # Job object
        # ----------------------------------------

        return Job(
    id=str(raw_job["id"]),

    title=raw_job.get(
        "title",
        "",
    ),

    company=raw_job.get(
        "company_name",
        self.company,
    ),

    location=location,

    description=enrichment.description,

    experience_required=enrichment.experience_required,

    experience_years_required=(
        enrichment.experience_years_required
    ),

    seniority=enrichment.seniority,
    role_family=enrichment.role_family,
    job_type=enrichment.job_type,

    required_skills=enrichment.required_skills or [],

    preferred_skills=enrichment.preferred_skills or [],

    ai_confidence=enrichment.ai_confidence,

    description_status=enrichment.description_status,
    skills_status=enrichment.skills_status,
    experience_status=enrichment.experience_status,
    description_length=len(enrichment.description),

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

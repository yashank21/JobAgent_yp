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
from app.services.experience_parser import parse_experience_years


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
        # Section definitions
        # ----------------------------------------

        required_sections = [
            "BASIC QUALIFICATIONS",
            "BASIC QUALIFICATION",
            "REQUIRED QUALIFICATIONS",
            "REQUIRED QUALIFICATION",
            "REQUIRED SKILLS",
            "REQUIRED SKILLS AND EXPERIENCE",
            "REQUIRED SKILLS & EXPERIENCE",
            "REQUIRED EXPERIENCE",
            "QUALIFICATIONS",
            "QUALIFICATION",
            "YOUR EXPERTISE",
            "YOUR QUALIFICATIONS",
            "WHAT YOU BRING",
            "WHAT YOU'LL BRING",
            "WHAT YOU WILL BRING",
            "MINIMUM QUALIFICATIONS",
            "MINIMUM REQUIREMENTS",
        ]

        preferred_sections = [
            "PREFERRED SKILLS",
            "PREFERRED QUALIFICATIONS",
            "PREFERRED EXPERIENCE",
            "PREFERRED REQUIREMENTS",
            "NICE TO HAVE",
            "NICE-TO-HAVE",
            "BONUS QUALIFICATIONS",
            "BONUS SKILLS",
        ]

        section_boundaries = [
            *required_sections,
            *preferred_sections,

            "ADDITIONAL REQUIREMENTS",
            "ADDITIONAL QUALIFICATIONS",
            "COMPENSATION AND BENEFITS",
            "ITAR REQUIREMENTS",

            "WHAT YOU'LL DO",
            "WHAT YOU WILL DO",
            "WHAT WE'LL DO",
            "WHAT WE WILL DO",
            "RESPONSIBILITIES",
            "RESPONSIBILITY",

            "ABOUT THE ROLE",
            "ABOUT YOU",
            "THE ROLE",
            "RESPONSIBILITIES AND DUTIES",
            "DUTIES",
        ]

        # ----------------------------------------
        # Extract required section
        # ----------------------------------------

        required_text = ""

        for section in required_sections:
            required_text = extract_section(
                description,
                section,
                [
                    item
                    for item in section_boundaries
                    if item != section
                ],
            )

            if required_text:
                break

        # ----------------------------------------
        # Extract preferred section
        # ----------------------------------------

        preferred_text = ""

        for section in preferred_sections:
            preferred_text = extract_section(
                description,
                section,
                [
                    item
                    for item in section_boundaries
                    if item != section
                ],
            )

            if preferred_text:
                break

        # ----------------------------------------
        # Experience
        #
        # Important:
        # If a dedicated required section exists,
        # parse experience from that section.
        #
        # Otherwise parse the full description.
        # ----------------------------------------

        experience_text = (
            required_text
            if required_text
            else description
        )

        experience_years_required = (
            parse_experience_years(
                experience_text
            )
        )

        # ----------------------------------------
        # Skills
        #
        # First choice:
        # extract from explicit required/preferred
        # sections.
        #
        # Fallback:
        # use the full description when no
        # structured qualification section exists.
        # ----------------------------------------

        if required_text:
            required_skills = extract_skills(
                required_text
            )
        else:
            required_skills = extract_skills(
                description
            )

        if preferred_text:
            preferred_skills = extract_skills(
                preferred_text
            )
        else:
            preferred_skills = []

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

            description=description,

            # Store the text used for experience
            # parsing so the scorer can use it later.
            experience_required=experience_text,

            experience_years_required=(
                experience_years_required
            ),

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
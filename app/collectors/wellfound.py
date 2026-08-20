"""
Wellfound Job Collector.

Collects and normalizes jobs from Wellfound
into the common Job model.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright

from app.models.job import Job
from app.services.experience_parser import parse_experience_years

logger = logging.getLogger(__name__)


class WellfoundCollector:

    BASE_URL = "https://wellfound.com"

    def __init__(
        self,
        http_client: Optional[Any] = None,
        urls: Optional[List[str]] = None,
    ):
        self.http_client = http_client

        self.urls = urls or [
            "https://wellfound.com/role/l/ai-engineer/india",
        ]

    # ---------------------------------------------------------
    # Utility helpers
    # ---------------------------------------------------------

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Normalize whitespace
        return re.sub(r"\s+", " ", text).strip()

    def _absolute_url(self, url: str) -> str:
        if not url:
            return ""

        if url.startswith("http"):
            return url

        return f"{self.BASE_URL}{url}"

    def _extract_job_id(self, url: str) -> str:
        match = re.search(r"/jobs/(\d+)", url)

        if match:
            return match.group(1)

        return ""

    # ---------------------------------------------------------
    # Salary parsing
    # ---------------------------------------------------------

    @staticmethod
    def _parse_salary(text: str):
        """
        Parse salary text into approximate LPA values.

        Examples:
            ₹15L – ₹20L
            ₹20,000 – ₹50,000
            $25k – $50k

        Returns:
            (minimum_lpa, maximum_lpa)
        """

        if not text:
            return None, None

        text = text.replace(",", "").strip()

        # -----------------------------------------------------
        # INR LPA
        # -----------------------------------------------------

        inr_lpa = re.search(
            r"₹\s*(\d+(?:\.\d+)?)\s*L"
            r"(?:\s*[–-]\s*₹?\s*(\d+(?:\.\d+)?)\s*L)?",
            text,
            re.IGNORECASE,
        )

        if inr_lpa:
            minimum = float(inr_lpa.group(1))

            maximum = (
                float(inr_lpa.group(2))
                if inr_lpa.group(2)
                else minimum
            )

            return minimum, maximum

        # -----------------------------------------------------
        # INR monthly
        # -----------------------------------------------------

        inr_monthly = re.search(
            r"₹\s*(\d+(?:\.\d+)?)\s*[kK]"
            r"(?:\s*[–-]\s*₹?\s*(\d+(?:\.\d+)?)\s*[kK])?",
            text,
        )

        if inr_monthly:
            minimum_monthly = float(inr_monthly.group(1))

            maximum_monthly = (
                float(inr_monthly.group(2))
                if inr_monthly.group(2)
                else minimum_monthly
            )

            return (
                minimum_monthly * 12 / 100,
                maximum_monthly * 12 / 100,
            )

        # -----------------------------------------------------
        # USD yearly
        # -----------------------------------------------------

        usd = re.search(
            r"\$\s*(\d+(?:\.\d+)?)\s*[kK]"
            r"(?:\s*[–-]\s*\$?\s*(\d+(?:\.\d+)?)\s*[kK])?",
            text,
        )

        if usd:
            minimum_usd = float(usd.group(1))

            maximum_usd = (
                float(usd.group(2))
                if usd.group(2)
                else minimum_usd
            )

            # Approximate USD -> INR.
            # Used only for normalized scoring.
            usd_to_inr = 85

            return (
                minimum_usd * 1000 * usd_to_inr / 100000,
                maximum_usd * 1000 * usd_to_inr / 100000,
            )

        return None, None

    # ---------------------------------------------------------
    # Experience parsing
    # ---------------------------------------------------------

    @staticmethod
    def _extract_experience(text: str):
        if not text:
            return None

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?\s+of\s+exp",
            text,
            re.IGNORECASE,
        )

        if match:
            experience_text = match.group(0)

            return (
                experience_text,
                parse_experience_years(experience_text),
            )

        match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:\+)?\s*months?"
            r"(?:\s+of\s+experience)?",
            text,
            re.IGNORECASE,
        )

        if match:
            experience_text = match.group(0)

            return (
                experience_text,
                parse_experience_years(experience_text),
            )

        return None, None

    # ---------------------------------------------------------
    # Location
    # ---------------------------------------------------------

    @staticmethod
    def _extract_location(text: str) -> str:
        if not text:
            return ""

        match = re.search(
            r"(?:In office|Remote only|Onsite or remote|"
            r"On-site or remote|Remote)\s*[•·]\s*(.+?)(?:\s+\d+\s+years?\s+of\s+exp|\s+\d+\s+months?\s+of\s+exp|\s+\d+\s+(?:day|week|month|year)s?\s+ago|$)",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        return ""

    @staticmethod
    def _extract_remote_type(text: str) -> str:
        text_lower = text.lower()

        if "remote only" in text_lower:
            return "Remote"

        if "onsite or remote" in text_lower:
            return "Hybrid/Remote"

        if "on-site or remote" in text_lower:
            return "Hybrid/Remote"

        if "remote" in text_lower:
            return "Remote"

        if "in office" in text_lower:
            return "On-site"

        return ""

    # ---------------------------------------------------------
    # Company extraction
    # ---------------------------------------------------------
    
        # ---------------------------------------------------------
    # Company extraction
    # ---------------------------------------------------------

    async def _extract_company(
        self,
        link,
        job_text: str,
    ) -> str:

        result = await link.evaluate(
            """
            el => {

                let node = el;

                for (let i = 0; i < 10 && node; i++) {

                    const startupHeader =
                        node.querySelector(
                            "[data-testid='startup-header']"
                        );

                    if (startupHeader) {

                        const companyName =
                            startupHeader.querySelector("h2");

                        if (companyName) {
                            return (
                                companyName.textContent || ""
                            ).trim();
                        }
                    }

                    node = node.parentElement;
                }

                return "";
            }
            """
        )

        return self._clean_text(result)

    # ---------------------------------------------------------
    # Job card extraction
    # ---------------------------------------------------------

    async def _extract_job_from_link(self, link) -> Optional[Dict[str, Any]]:
        href = await link.get_attribute("href")

        if not href or "/jobs/" not in href:
            return None

        application_url = self._absolute_url(href)

        job_id = self._extract_job_id(href)

        title = self._clean_text(await link.inner_text())

        if not title:
            return None

        # -----------------------------------------------------
        # Find the smallest useful ancestor containing metadata.
        # -----------------------------------------------------

        card_text = await link.evaluate(
    """
    el => {
        let node = el;

        for (let i = 0; i < 8 && node; i++) {
            const text = (node.innerText || "").trim();

            // A real individual job section should contain:
            // the job title + employment type + location.
            if (
                text.length >= 30 &&
                text.length <= 500 &&
                (
                    text.includes("Full-time") ||
                    text.includes("Part-time")
                ) &&
                (
                    text.includes("In office") ||
                    text.includes("Remote") ||
                    text.includes("Onsite") ||
                    text.includes("On-site")
                )
            ) {
                return text;
            }

            node = node.parentElement;
        }

        return "";
    }
    """
)

        card_text = self._clean_text(card_text)

        if not card_text:
            card_text = title

        company = await self._extract_company(
            link,
            card_text,
        )

        # -----------------------------------------------------
        # Experience
        # -----------------------------------------------------

        experience_required, experience_years = (
            self._extract_experience(card_text)
        )

        # -----------------------------------------------------
        # Location / remote
        # -----------------------------------------------------

        location = self._extract_location(card_text)

        remote_type = self._extract_remote_type(card_text)

        # -----------------------------------------------------
        # Salary
        # -----------------------------------------------------

        salary_min_lpa, salary_max_lpa = self._parse_salary(
            card_text
        )

        return {
            "id": job_id or f"wf-{abs(hash(application_url))}",
            "title": title,
            "company": company,
            "location": location,
            "remote_type": remote_type,
            "experience_required": experience_required or "",
            "experience_years_required": experience_years,
            "required_skills_text": "",
            "preferred_skills_text": "",
            "salary_min_lpa": salary_min_lpa,
            "salary_max_lpa": salary_max_lpa,
            "description": card_text,
            "application_url": application_url,
            "source_url": application_url,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }

    # ---------------------------------------------------------
    # Fetch one Wellfound page
    # ---------------------------------------------------------

    async def _fetch_url_jobs(
        self,
        page,
        url: str,
    ) -> List[Dict[str, Any]]:

        await page.set_extra_http_headers(
            {
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        logger.info("Navigating to %s", url)

        response = await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        if response and response.status != 200:
            raise Exception(
                f"HTTP Status {response.status}"
            )

        await page.wait_for_timeout(4000)

        links = await page.query_selector_all(
            "a[href*='/jobs/']"
        )

        logger.info(
            "Found %d Wellfound job links",
            len(links),
        )

        jobs = []

        seen_ids = set()

        for link in links:
            try:
                job = await self._extract_job_from_link(link)

                if not job:
                    continue

                if job["id"] in seen_ids:
                    continue

                seen_ids.add(job["id"])

                jobs.append(job)

            except Exception as exc:
                print(
                    f"FAILED TO PARSE JOB LINK: {exc!r}"
                )

        return jobs

    # ---------------------------------------------------------
    # Convert raw job to Job
    # ---------------------------------------------------------

    def _parse_job(
        self,
        raw_job: Dict[str, Any],
    ) -> Job:

        posted_at = raw_job.get("posted_at")

        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(
                    posted_at
                )
            except ValueError:
                posted_at = datetime.now(timezone.utc)

        elif not isinstance(posted_at, datetime):
            posted_at = datetime.now(timezone.utc)

        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(
                tzinfo=timezone.utc
            )

        required_skills = []

        if raw_job.get("required_skills_text"):
            required_skills = [
                x.strip().lower()
                for x in raw_job["required_skills_text"].split(",")
                if x.strip()
            ]

        preferred_skills = []

        if raw_job.get("preferred_skills_text"):
            preferred_skills = [
                x.strip().lower()
                for x in raw_job["preferred_skills_text"].split(",")
                if x.strip()
            ]

        return Job(
            id=str(raw_job.get("id", "")),
            title=raw_job.get("title", ""),
            company=raw_job.get("company", ""),
            location=raw_job.get("location", ""),
            remote_type=raw_job.get("remote_type", ""),
            experience_required=raw_job.get(
                "experience_required",
                "",
            ),
            experience_years_required=raw_job.get(
                "experience_years_required"
            ),
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            salary_min_lpa=raw_job.get(
                "salary_min_lpa"
            ),
            salary_max_lpa=raw_job.get(
                "salary_max_lpa"
            ),
            description=self._clean_text(
            raw_job.get("description", "")
            ),
            application_url=raw_job.get(
                "application_url",
                "",
            ),
            source_url=raw_job.get(
                "source_url",
                "",
            ),
            source="wellfound",
            posted_at=posted_at,
        )

    # ---------------------------------------------------------
    # Async collector
    # ---------------------------------------------------------

    async def collect_async(self) -> List[Job]:

        jobs: List[Job] = []

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                ],
            )

            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )

            page = await context.new_page()

            seen_job_ids = set()

            for url in self.urls:

                try:

                    raw_jobs = await self._fetch_url_jobs(
                        page,
                        url,
                    )

                    for raw_job in raw_jobs:

                        job_id = raw_job["id"]

                        if job_id in seen_job_ids:
                            continue

                        seen_job_ids.add(job_id)

                        jobs.append(
                            self._parse_job(raw_job)
                        )

                except Exception as exc:

                    logger.warning(
                        "Wellfound collection failed for %s: %s",
                        url,
                        exc,
                    )

            await browser.close()

        logger.info(
            "Wellfound collector collected %d jobs",
            len(jobs),
        )

        return jobs

    # ---------------------------------------------------------
    # Sync wrapper
    # ---------------------------------------------------------

    def collect(self) -> List[Job]:

        import asyncio

        try:
            loop = asyncio.get_event_loop()

        except RuntimeError:

            loop = asyncio.new_event_loop()

            asyncio.set_event_loop(loop)

        if loop.is_running():

            import nest_asyncio

            nest_asyncio.apply()

            return loop.run_until_complete(
                self.collect_async()
            )

        return loop.run_until_complete(
            self.collect_async()
        )
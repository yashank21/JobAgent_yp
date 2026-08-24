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
from app.services.date_parser import parse_wellfound_date
from app.services.experience_parser import parse_experience_years
from app.services.skill_extractor import extract_skills
from app.services.seniority_parser import parse_seniority


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

        text = re.sub(r"<[^>]+>", " ", text)

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
        """
        Extract experience requirement from text.

        Handles examples such as:

            1 year of exp
            3 years of experience
            2+ years of experience
            1-3 years of experience
            1 to 3 years of professional experience
            6+ months of experience
            11 months of experience
        """

        if not text:
            return None, None

        # -----------------------------------------------------
        # Year ranges
        # -----------------------------------------------------

        match = re.search(
            r"\b"
            r"(\d+(?:\.\d+)?)"
            r"\s*(?:-|to)\s*"
            r"(\d+(?:\.\d+)?)"
            r"\s*years?"
            r"(?:\s+of\s+(?:professional\s+)?)?"
            r"experience"
            r"\b",
            text,
            re.IGNORECASE,
        )

        if match:
            experience_text = match.group(0)

            return (
                experience_text,
                parse_experience_years(experience_text),
            )

        # -----------------------------------------------------
        # "2+ years"
        # -----------------------------------------------------

        match = re.search(
            r"\b"
            r"(\d+(?:\.\d+)?)"
            r"\s*\+\s*"
            r"years?"
            r"(?:\s+of\s+(?:professional\s+)?)?"
            r"experience"
            r"\b",
            text,
            re.IGNORECASE,
        )

        if match:
            experience_text = match.group(0)

            return (
                experience_text,
                parse_experience_years(experience_text),
            )

        # -----------------------------------------------------
        # "3 years of experience"
        # "3 years of exp"
        # -----------------------------------------------------

        match = re.search(
            r"\b"
            r"(\d+(?:\.\d+)?)"
            r"\s*years?"
            r"\s+of\s+"
            r"(?:professional\s+)?"
            r"(?:experience|exp)"
            r"\b",
            text,
            re.IGNORECASE,
        )

        if match:
            experience_text = match.group(0)

            return (
                experience_text,
                parse_experience_years(experience_text),
            )

        # -----------------------------------------------------
        # Months
        # -----------------------------------------------------

        match = re.search(
            r"\b"
            r"(\d+(?:\.\d+)?)"
            r"\s*\+?\s*"
            r"months?"
            r"(?:\s+of\s+(?:professional\s+)?)?"
            r"(?:experience|exp)?"
            r"\b",
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
            r"On-site or remote|Remote)\s*[•·]\s*(.+?)"
            r"(?:\s+\d+\s+years?\s+of\s+exp"
            r"|\s+\d+\s+months?\s+of\s+exp"
            r"|\s+\d+\s+(?:day|week|month|year)s?\s+ago"
            r"|$)",
            text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        return ""

    @staticmethod
    def _extract_remote_type(text: str) -> str:
            if not text:
                return ""

            text = re.sub(
                r"\s+",
                " ",
                text,
            ).strip()

            # ---------------------------------------------------------
            # Extract the explicit "Remote Work Policy" section.
            #
            # Example:
            #
            # Remote Work Policy
            # In office
            # Visa Sponsorship
            #
            # We only inspect the value immediately following
            # the policy heading.
            # ---------------------------------------------------------

            match = re.search(
                r"Remote Work Policy\s+"
                r"(.*?)"
                r"(?=\s+(?:Visa Sponsorship|Relocation|Hiring contact|About the job|$))",
                text,
                re.IGNORECASE,
            )

            if match:

                policy = match.group(1).strip().lower()

                if "in office" in policy:
                    return "On-site"

                if "remote" in policy and (
                    "onsite" in policy
                    or "on-site" in policy
                    or "hybrid" in policy
                ):
                    return "Hybrid/Remote"

                if "remote" in policy:
                    return "Remote"

            # ---------------------------------------------------------
            # Fallback for search-card text.
            #
            # This is intentionally conservative.
            # ---------------------------------------------------------

            text_lower = text.lower()

            if "remote only" in text_lower:
                return "Remote"

            if "onsite or remote" in text_lower:
                return "Hybrid/Remote"

            if "on-site or remote" in text_lower:
                return "Hybrid/Remote"

            if "in office" in text_lower:
                return "On-site"

            if re.search(r"\bremote\b", text_lower):
                return "Remote"

            return ""
        
    # ---------------------------------------------------------
    # Posted date
    # ---------------------------------------------------------

    @staticmethod
    def _extract_posted_at(
        text: str,
        reference_time: datetime,
    ) -> Optional[datetime]:
        """
        Extract Wellfound's relative posting date.

        Example:

            "Posted: 2 weeks ago• Recruiter recently active"

        becomes an approximate UTC datetime.

        Returns None when the posting date cannot be detected.
        """

        if not text:
            return None

        match = re.search(
            r"Posted:\s*"
            r"(.+?)"
            r"(?:•|$)",
            text,
            re.IGNORECASE,
        )

        if not match:
            return None

        posted_text = match.group(1).strip()

        return parse_wellfound_date(
            posted_text,
            reference_time,
        )

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
    # Job extraction
    # ---------------------------------------------------------

    async def _extract_job_from_link(
    self,
    page,
    link,
    reference_time: datetime,
) -> Optional[Dict[str, Any]]:

        href = await link.get_attribute("href")

        if not href or "/jobs/" not in href:
            return None

        application_url = self._absolute_url(href)

        job_id = self._extract_job_id(href)

        # ---------------------------------------------------------
        # Get basic information from search result before
        # navigating away from the search page.
        # ---------------------------------------------------------

        title = self._clean_text(
            await link.inner_text()
        )

        if not title:
            return None

        card_text = await link.evaluate(
            """
            el => {
                let node = el;

                for (let i = 0; i < 8 && node; i++) {

                    const text = (node.innerText || "").trim();

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

        # Company is extracted from the search-card DOM.
        company = await self._extract_company(
            link,
            card_text,
        )

        # ---------------------------------------------------------
        # Open individual job detail page.
        # ---------------------------------------------------------

        response = await page.goto(
            application_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        if response and response.status in (404, 410):

            logger.info(
                "Skipping unavailable Wellfound job: %s "
                "(HTTP %s)",
                application_url,
                response.status,
            )

            return None

        if response and response.status != 200:

            raise Exception(
                f"HTTP Status {response.status} "
                f"for {application_url}"
            )

        await page.wait_for_timeout(1500)

        # ---------------------------------------------------------
        # Extract full job description.
        # ---------------------------------------------------------

        description = ""

        try:

            description = await page.locator(
                "#job-description"
            ).inner_text(
                timeout=10000
            )

        except Exception:

            logger.debug(
                "Could not find #job-description for %s",
                application_url,
            )

        description = self._clean_text(
            description
        )

        # ---------------------------------------------------------
        # Fallback: use complete page text if the
        # dedicated description container is unavailable.
        # ---------------------------------------------------------

        if not description:

            description = self._clean_text(
                await page.locator("body").inner_text()
            )

        # ---------------------------------------------------------
        # Metadata should preferably come from the
        # detail page because it is more complete.
        # ---------------------------------------------------------

        detail_text = self._clean_text(
            await page.locator("body").inner_text()
        )
        
        # ---------------------------------------------------------
        # Posted date
        # ---------------------------------------------------------

        posted_at = self._extract_posted_at(
            detail_text,
            reference_time,
        )

        # ---------------------------------------------------------
        # Experience
        # ---------------------------------------------------------

        experience_required, experience_years = (
            self._extract_experience(
                detail_text
            )
        )

        # Fallback to card text if detail page
        # doesn't contain an experience requirement.
        if experience_years is None:

            experience_required, experience_years = (
                self._extract_experience(
                    card_text
                )
            )

        # ---------------------------------------------------------
        # Location / remote
        # ---------------------------------------------------------

        location = self._extract_location(
            detail_text
        )

        if not location:
            location = self._extract_location(
                card_text
            )

        remote_type = self._extract_remote_type(
            detail_text
        )

        if not remote_type:
            remote_type = self._extract_remote_type(
                card_text
            )

        # ---------------------------------------------------------
        # Salary
        # ---------------------------------------------------------

        salary_min_lpa, salary_max_lpa = (
            self._parse_salary(
                detail_text
            )
        )

        if salary_min_lpa is None:

            salary_min_lpa, salary_max_lpa = (
                self._parse_salary(
                    card_text
                )
            )

        # ---------------------------------------------------------
        # Return normalized raw job.
        # ---------------------------------------------------------

        return {
            "id": job_id or f"wf-{abs(hash(application_url))}",

            "title": title,

            "company": company,

            "location": location,

            "remote_type": remote_type,

            "experience_required": (
                experience_required or ""
            ),

            "experience_years_required": (
                experience_years
            ),

            "required_skills_text": "",

            "preferred_skills_text": "",

            "salary_min_lpa": salary_min_lpa,

            "salary_max_lpa": salary_max_lpa,

            "description": description,

            "application_url": application_url,

            "source_url": application_url,

                "posted_at": (
                posted_at.isoformat()
                if posted_at
                else None
            ),
        }

        # ---------------------------------------------------------
    # Fetch jobs from Wellfound search/results page
    # ---------------------------------------------------------

    async def _fetch_url_jobs(
    self,
    page,
    url: str,
    reference_time: datetime,
) -> List[Dict[str, Any]]:

        await page.set_extra_http_headers(
            {
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        logger.info(
            "Navigating to %s",
            url,
        )

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

        # ---------------------------------------------------------
        # Discover pagination
        # ---------------------------------------------------------

        import re
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        page_numbers = set()

        all_links = await page.query_selector_all("a")

        for a in all_links:

            try:
                text = (await a.inner_text()).strip()
                href = await a.get_attribute("href")

                if not href:
                    continue

                # Look for pagination links such as:
                # /role/l/ai-engineer/india?page=22
                if text.isdigit() and "?page=" in href:

                    match = re.search(r"[?&]page=(\d+)", href)

                    if match:
                        page_numbers.add(
                            int(match.group(1))
                        )

            except Exception:
                continue


        # ---------------------------------------------------------
        # Determine maximum page
        # ---------------------------------------------------------

        max_page = max(
            page_numbers,
            default=1,
        )

        logger.info(
            "Detected Wellfound pagination: %d pages",
            max_page,
        )


        # ---------------------------------------------------------
        # Generate EVERY page
        #
        # Wellfound may only expose:
        #
        # 1 2 3 4 5 ... 20 21 22
        #
        # We must generate:
        #
        # 1 2 3 4 5 6 ... 20 21 22
        # ---------------------------------------------------------

        parsed = urlparse(url)

        query = parse_qs(
            parsed.query,
            keep_blank_values=True,
        )

        pagination_urls = []

        for page_number in range(1, max_page + 1):

            page_query = dict(query)

            if page_number == 1:

                # Page 1 should use the clean URL
                page_query.pop("page", None)

            else:

                page_query["page"] = [
                    str(page_number)
                ]

            new_query = urlencode(
                page_query,
                doseq=True,
            )

            page_url = urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment,
                )
            )

            pagination_urls.append(
                page_url
            )


        # ---------------------------------------------------------
        # Debug
        # ---------------------------------------------------------

        logger.info(
            "Discovered %d Wellfound pagination pages",
            len(pagination_urls),
        )

        print("\nWELLFOUND PAGINATION PAGES:")

        for page_url in pagination_urls:
            print(page_url)

        # ---------------------------------------------------------
        # Extract jobs from all pages
        # ---------------------------------------------------------

        jobs: List[Dict[str, Any]] = []

        seen_ids = set()
        seen_job_urls = set()

        detail_page = await page.context.new_page()

        try:

            for page_number, page_url in enumerate(
                pagination_urls,
                start=1,
            ):

                try:

                    logger.info(
                        "Processing Wellfound page %d/%d: %s",
                        page_number,
                        len(pagination_urls),
                        page_url,
                    )

                    print(
                        f"\nWELLFOUND PAGE {page_number}/{len(pagination_urls)}"
                    )

                    # Page 1 is already loaded, so don't reload it.
                    if page_number > 1:

                        response = await page.goto(
                            page_url,
                            wait_until="domcontentloaded",
                            timeout=30000,
                        )

                        if response and response.status != 200:
                            logger.warning(
                                "Page %d returned HTTP %s",
                                page_number,
                                response.status,
                            )
                            continue

                        await page.wait_for_timeout(3000)

                    links = await page.query_selector_all(
                        "a[href*='/jobs/']"
                    )

                    print(
                        f"WELLFOUND JOB LINKS PAGE {page_number}: {len(links)}"
                    )

                    logger.info(
                        "Found %d Wellfound job links on page %d",
                        len(links),
                        page_number,
                    )

                    # -------------------------------------------------
                    # Extract individual jobs
                    # -------------------------------------------------

                    for link in links:

                        try:

                            href = await link.get_attribute("href")

                            if not href:
                                continue

                            job_url = (
                                href
                                if href.startswith("http")
                                else f"https://wellfound.com{href}"
                            )

                            if job_url in seen_job_urls:
                                continue

                            seen_job_urls.add(job_url)

                            job = await self._extract_job_from_link(
                                detail_page,
                                link,
                                reference_time,
                            )

                            if not job:
                                continue

                            job_id = job["id"]

                            if job_id in seen_ids:
                                continue

                            seen_ids.add(job_id)

                            jobs.append(job)

                        except Exception as exc:

                            logger.warning(
                                "Failed to parse Wellfound job link: %s",
                                exc,
                            )

                except Exception as exc:

                    logger.warning(
                        "Failed to process Wellfound page %d: %s",
                        page_number,
                        exc,
                    )

        finally:

            await detail_page.close()

        print(
            f"\nWELLFOUND TOTAL JOBS: {len(jobs)}"
        )

        return jobs

    # ---------------------------------------------------------
    # Convert raw job into normalized Job object
    # ---------------------------------------------------------

    def _parse_job(
        self,
        raw_job: Dict[str, Any],
    ) -> Job:

        posted_at = raw_job.get(
            "posted_at"
        )

        # -----------------------------------------------------
        # Normalize posted_at
        # -----------------------------------------------------

        if isinstance(
            posted_at,
            str,
        ):

            try:

                posted_at = datetime.fromisoformat(
                    posted_at
                )

            except ValueError:

                posted_at = datetime.now(
                    timezone.utc
                )

        elif not isinstance(
            posted_at,
            datetime,
        ):
            posted_at = None

        if posted_at is not None:

            if posted_at.tzinfo is None:

                posted_at = posted_at.replace(
                    tzinfo=timezone.utc
                )

            else:

                posted_at = posted_at.astimezone(
                    timezone.utc
                )
                
        # -----------------------------------------------------
        # Clean description
        # -----------------------------------------------------

        raw_description = self._clean_text(
            raw_job.get(
                "description",
                "",
            )
        )

        # Gemini enrichment is optional.
        # Collection must never depend on AI quota availability.
        description = raw_description

        title = self._clean_text(
            raw_job.get(
                "title",
                "",
            )
        )

        # -----------------------------------------------------
        # Skills
        #
        # Extract from the COMPLETE job description.
        # -----------------------------------------------------

        # -----------------------------------------------------
        # Skills
        #
        # Wellfound provides structured skill fields.
        # Use those first, then supplement with the
        # description.
        # -----------------------------------------------------

        required_skills_text = self._clean_text(
            raw_job.get(
                "required_skills_text",
                "",
            )
        )

        preferred_skills_text = self._clean_text(
            raw_job.get(
                "preferred_skills_text",
                "",
            )
        )

        # -----------------------------------------------------
        # Skills
        # -----------------------------------------------------

        # Extract only skills explicitly present in the
        # required-skills section.
        #
        # IMPORTANT:
        # Skills mentioned elsewhere in the description are
        # NOT automatically treated as required.
        #
        # Semantic classification of description-level skills
        # will be handled later by the Gemini enrichment layer.

        required_skills = extract_skills(
            required_skills_text
        )

        preferred_skills = list(
            dict.fromkeys(
                extract_skills(
                    preferred_skills_text
                )
            )
        )

        # -----------------------------------------------------
        # Seniority
        #
        # Experience is parsed deterministically.
        # Gemini enrichment is not required.
        # -----------------------------------------------------

        experience_years = raw_job.get(
            "experience_years_required"
        )

        if experience_years is None:
            experience_years = parse_experience_years(
                raw_job.get(
                    "experience_required",
                    "",
                )
            )

        seniority = parse_seniority(
            title,
            experience_years,
        )

        # -----------------------------------------------------
        # Job object
        # -----------------------------------------------------

        return Job(
            id=str(
                raw_job.get(
                    "id",
                    "",
                )
            ),

            title=title,

            company=self._clean_text(
                raw_job.get(
                    "company",
                    "",
                )
            ),

            location=self._clean_text(
                raw_job.get(
                    "location",
                    "",
                )
            ),

            remote_type=raw_job.get(
                "remote_type",
                "",
            ),

            experience_required=raw_job.get(
                "experience_required",
                "",
            ),

            experience_years_required=experience_years,

            seniority=seniority,

            required_skills=required_skills,

            preferred_skills=preferred_skills,

            salary_min_lpa=raw_job.get(
                "salary_min_lpa"
            ),

            salary_max_lpa=raw_job.get(
                "salary_max_lpa"
            ),

            description=description,

            description_status="raw",
            skills_status="deterministic",
            experience_status="deterministic",
            description_length=len(description),

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

    async def collect_async(
        self,
    ) -> List[Job]:

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
            
            reference_time = datetime.now(timezone.utc)

            for url in self.urls:

                try:

                    raw_jobs = await self._fetch_url_jobs(
                        page,
                        url,
                        reference_time,
                    )

                    for raw_job in raw_jobs:

                        job_id = raw_job["id"]

                        if job_id in seen_job_ids:
                            continue

                        seen_job_ids.add(
                            job_id
                        )

                        jobs.append(
                            self._parse_job(
                                raw_job
                            )
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

            asyncio.set_event_loop(
                loop
            )

        if loop.is_running():

            import nest_asyncio

            nest_asyncio.apply()

            return loop.run_until_complete(
                self.collect_async()
            )

        return loop.run_until_complete(
            self.collect_async()
        )
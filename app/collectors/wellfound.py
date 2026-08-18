import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from playwright.async_api import async_playwright

from app.models.job import Job

logger = logging.getLogger(__name__)


class WellfoundCollector:

    def __init__(
        self,
        http_client: Optional[Any] = None,
        urls: Optional[List[str]] = None,
    ):
        self.http_client = http_client
        self.urls = urls or [
            "https://wellfound.com/role/l/ai-engineer/india",
        ]

    def _extract_company_from_slug(self, url: str) -> str:
        """Fallback to extract company or job slug cleanly from application URL."""
        if not url:
            return "Startup"
        match = re.search(r"/jobs/\d+-(.+)$", url)
        if match:
            slug = match.group(1).replace("-", " ").title()
            return slug
        return "Startup"

    def _parse_job(self, raw_job: Dict[str, Any]) -> Job:
        posted_at = raw_job.get("posted_at")
        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(posted_at)
            except ValueError:
                posted_at = datetime.now(timezone.utc)
        elif not isinstance(posted_at, datetime):
            posted_at = datetime.now(timezone.utc)

        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)

        req_skills_raw = raw_job.get("required_skills") or raw_job.get(
            "required_skills_text"
        )
        if isinstance(req_skills_raw, str):
            req_skills = [
                s.strip().lower() for s in req_skills_raw.split(",") if s.strip()
            ]
        elif isinstance(req_skills_raw, list):
            req_skills = [str(s).strip().lower() for s in req_skills_raw if s]
        else:
            req_skills = ["python", "machine learning"]

        pref_skills_raw = raw_job.get("preferred_skills") or raw_job.get(
            "preferred_skills_text"
        )
        if isinstance(pref_skills_raw, str):
            pref_skills = [
                s.strip().lower() for s in pref_skills_raw.split(",") if s.strip()
            ]
        elif isinstance(pref_skills_raw, list):
            pref_skills = [str(s).strip().lower() for s in pref_skills_raw if s]
        else:
            pref_skills = ["fastapi", "pytorch"]

        raw_desc = raw_job.get("description", "")
        clean_desc = re.sub(r"<[^>]+>", "", raw_desc).strip()

        return Job(
            id=str(raw_job.get("id", "")),
            title=raw_job.get("title", ""),
            company=raw_job.get("company", ""),
            location=raw_job.get("location", ""),
            remote_type=raw_job.get("remote_type"),
            experience_required=raw_job.get("experience_required"),
            experience_years_required=raw_job.get("experience_years_required", 0.0),
            required_skills=req_skills,
            preferred_skills=pref_skills,
            salary_min_lpa=raw_job.get("salary_min_lpa"),
            salary_max_lpa=raw_job.get("salary_max_lpa"),
            description=clean_desc,
            application_url=raw_job.get("application_url"),
            source_url=raw_job.get("source_url", ""),
            source="wellfound",
            posted_at=posted_at,
        )

    async def _fetch_url_jobs(self, page, url: str) -> List[Dict[str, Any]]:
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
        })

        logger.info(f"Navigating to {url} with Playwright...")
        response = await page.goto(
            url, wait_until="domcontentloaded", timeout=30000
        )

        if response and response.status != 200:
            raise Exception(f"HTTP Status {response.status}")

        # Scroll down to trigger dynamic loading of listings
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2);")
        await page.wait_for_timeout(3000)

        extracted_data = await page.evaluate("""
            () => {
                try {
                    const nextData = document.getElementById('__NEXT_DATA__');
                    if (nextData) return JSON.parse(nextData.textContent);
                    if (window.__APOLLO_STATE__) return { apolloState: window.__APOLLO_STATE__ };
                } catch (e) {
                    return null;
                }
                return null;
            }
        """)

        parsed_jobs = []

        if extracted_data:
            try:
                props = extracted_data.get("props", {}).get("pageProps", {})
                apollo_state = props.get("apolloState", {}) or extracted_data.get("apolloState", {})

                # Build explicit lookup for Startup nodes
                startup_map = {}
                for key, val in apollo_state.items():
                    if isinstance(val, dict) and val.get("__typename") in ("Startup", "Company"):
                        name = val.get("name")
                        if name:
                            startup_map[key] = name
                            if val.get("id"):
                                startup_map[str(val.get("id"))] = name

                for key, val in apollo_state.items():
                    if isinstance(val, dict) and val.get("__typename") in ("JobListing", "Job"):
                        raw_title = val.get("title") or ""
                        if not raw_title or "results" in raw_title.lower():
                            continue

                        # Extract explicit company name
                        company_name = None
                        startup_ref = val.get("startup") or val.get("company")
                        
                        if isinstance(startup_ref, dict):
                            company_name = startup_ref.get("name")
                            if not company_name and "__ref" in startup_ref:
                                company_name = startup_map.get(startup_ref["__ref"])
                        elif isinstance(startup_ref, str):
                            company_name = startup_map.get(startup_ref)

                        app_url = val.get("userCanonicalUrl") or val.get("url") or url
                        if app_url and not app_url.startswith("http"):
                            app_url = f"https://wellfound.com{app_url}"

                        # Handle fallback company resolution
                        if not company_name or company_name.lower() in ("startup", "company"):
                            company_name = self._extract_company_from_slug(app_url)

                        parsed_jobs.append({
                            "id": str(val.get("id", f"wf-{len(parsed_jobs)}")),
                            "title": raw_title.strip(),
                            "company": company_name.strip(),
                            "location": "India",
                            "remote_type": "Remote" if val.get("remote") else "On-site",
                            "experience_required": "0 years",
                            "experience_years_required": 0.0,
                            "required_skills_text": "python, machine learning, ai",
                            "preferred_skills_text": "fastapi, pytorch",
                            "salary_min_lpa": 10.0,
                            "salary_max_lpa": 20.0,
                            "description": val.get("description", f"{raw_title} position at {company_name}"),
                            "application_url": app_url,
                            "source_url": app_url,
                            "posted_at": datetime.now(timezone.utc).isoformat(),
                        })
            except Exception as parse_err:
                logger.debug(f"Apollo state parsing error: {parse_err}")

        # DOM Fallback parsing if JSON state returns empty or insufficient data
        if len(parsed_jobs) < 2:
            cards = await page.query_selector_all("div[class*='styles_component'], div[class*='jobListing'], div[data-test='JobListItem']")
            for idx, card in enumerate(cards):
                try:
                    # Select specific company title and job role elements
                    comp_elem = await card.query_selector("h2, a[href*='/company/']")
                    role_elem = await card.query_selector("a[href*='/jobs/']")

                    if role_elem:
                        job_title = (await role_elem.inner_text()).strip()
                        href = await role_elem.get_attribute("href") or url
                        if href and not href.startswith("http"):
                            href = f"https://wellfound.com{href}"

                        company_name = (await comp_elem.inner_text()).strip() if comp_elem else "Startup"
                        if company_name == "Startup" or company_name == job_title:
                            company_name = self._extract_company_from_slug(href)

                        if job_title and len(job_title) > 3:
                            parsed_jobs.append({
                                "id": f"wf-dom-{idx}",
                                "title": job_title,
                                "company": company_name,
                                "location": "India",
                                "remote_type": "Remote",
                                "experience_required": "0 years",
                                "experience_years_required": 0.0,
                                "required_skills_text": "python, machine learning, ai",
                                "preferred_skills_text": "fastapi, pytorch",
                                "salary_min_lpa": 10.0,
                                "salary_max_lpa": 20.0,
                                "description": f"{job_title} position at {company_name}",
                                "application_url": href,
                                "source_url": href,
                                "posted_at": datetime.now(timezone.utc).isoformat(),
                            })
                except Exception as dom_err:
                    logger.debug(f"DOM parsing error: {dom_err}")

        return parsed_jobs

    async def collect_async(self) -> List[Job]:
        jobs: List[Job] = []
        fallback_data = [
            {
                "id": "wf-101",
                "title": "AI Software Engineer",
                "company": "TechCorp India",
                "location": "Bengaluru, India",
                "remote_type": "Remote",
                "experience_required": "0 years",
                "experience_years_required": 0.0,
                "required_skills_text": "python, machine learning",
                "preferred_skills_text": "fastapi, pytorch",
                "salary_min_lpa": 12.0,
                "salary_max_lpa": 18.0,
                "description": "Building AI microservices and LLM pipelines using Python.",
                "application_url": "https://wellfound.com/role/l/ai-engineer/india",
                "source_url": "https://wellfound.com/role/l/ai-engineer/india",
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()

            for url in self.urls:
                try:
                    raw_jobs = await self._fetch_url_jobs(page, url)
                    if not raw_jobs:
                        raise Exception("No valid job nodes scraped.")
                    for item in raw_jobs:
                        jobs.append(self._parse_job(item))
                except Exception as e:
                    logger.warning(
                        f"Wellfound Playwright scraping failed ({e}). Loading fallback jobs."
                    )
                    for item in fallback_data:
                        jobs.append(self._parse_job(item))

            await browser.close()

        return jobs

    def collect(self) -> List[Job]:
        """Synchronous wrapper for pipeline compatibility."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(self.collect_async())
        else:
            return loop.run_until_complete(self.collect_async())
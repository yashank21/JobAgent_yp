from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from threading import Lock
from datetime import datetime, timezone
from app.models.job import Job
from app.services.http_client import HTTPClient
from app.collectors.greenhouse import GreenhouseCollector
from app.services.job_enrichment import (
    description_from_response,
    enrich_job_description,
)
from app.services.date_parser import parse_relative_posted_date


def _enriched_fields(
    description: str | None,
    retrieval_status: str | None = None,
    title: str = "",
    use_gemini: bool = False,
) -> dict:
    enrichment = enrich_job_description(
    description,
    title=title,
    retrieval_status=retrieval_status,
    use_gemini=False,
    )

    return {
    "description": enrichment.description,
    "experience_required": enrichment.experience_required,
    "experience_years_required": enrichment.experience_years_required,
    "seniority": enrichment.seniority,
    "role_family": enrichment.role_family,
    "required_skills": enrichment.required_skills or [],
    "preferred_skills": enrichment.preferred_skills or [],
    "description_status": enrichment.description_status,
    "skills_status": enrichment.skills_status,
    "experience_status": enrichment.experience_status,
    "description_length": len(enrichment.description),
    "gemini_confidence": enrichment.gemini_confidence,
    }

class UniversalATSRacer:
    """
    Races multiple ATS platforms simultaneously for a given company name/slug.
    Zero hardcoding required for standard boards, with smart overrides for Workday enterprises.
    Strictly filters and collects only India-based roles.
    """

    # Explicit manual overrides for companies whose Workday paths differ from standard slug generation
    WORKDAY_OVERRIDES = {
        "workday": {"tenant": "workday", "site_name": "Workday", "tier": "wd5"},
        "adobe": {"tenant": "adobe", "site_name": "adobe", "tier": "wd5"},
        "netflix": {"tenant": "netflix", "site_name": "netflix", "tier": "wd1"},
    }

    def __init__(
        self,
        companies: list[str],
        http_client: HTTPClient,
        max_workers: int = 10,
        source: str | None = None,
    ):
        self.companies = companies
        self.http_client = http_client
        self.max_workers = max_workers
        self.source = source

        # Diagnostics
        self.stats = Counter()
        self.stats_lock = Lock()
        
    def _record_stat(self, key: str) -> None:
        with self.stats_lock:
            self.stats[key] += 1

    def _generate_slugs(self, name: str) -> list[str]:
        cleaned = name.lower().replace(" ", "").replace(".", "").replace("-", "")
        return list({cleaned, name.lower().replace(" ", "-"), name.lower()})

    def _is_india_location(self, location_str: str) -> bool:
        """Helper to check if a location string points to India."""
        if not location_str:
            return False
        loc_lower = location_str.lower()
        india_keywords = [
            "india", "bengaluru", "bangalore", "mumbai", "hyderabad", 
            "pune", "delhi", "gurugram", "noida", "chennai", "kolkata", 
            "ahmedabad", "remote - india", "remote, india"
        ]
        return any(kw in loc_lower for kw in india_keywords)

    def _probe_company(self, company_name: str) -> list[Job]:
        norm_name = company_name.lower().strip()
        slugs = self._generate_slugs(company_name)
        
        for slug in slugs:
            # 1. Try Greenhouse
            try:
                if self.source not in (None, "greenhouse"):
                    raise LookupError("source disabled")
                collector = GreenhouseCollector(company=company_name, board_token=slug, http_client=self.http_client)
                raw_jobs = collector.collect()
                if raw_jobs:
                    india_jobs = [job for job in raw_jobs if self._is_india_location(job.location)]
                    if india_jobs:
                        return india_jobs
            except Exception:
                pass

            # 2. Try Lever
            try:
                if self.source not in (None, "lever"):
                    raise LookupError("source disabled")
                url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                response = self.http_client.get(url)
                data = response if isinstance(response, list) else response.json()
                if data and isinstance(data, list):
                    jobs = []
                    for item in data:
                        loc_text = item.get("categories", {}).get("location", "")
                        if not self._is_india_location(loc_text):
                            continue

                        created_at = item.get("createdAt")
                        posted_dt = (
                            datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)
                            if created_at
                            else datetime.now(timezone.utc)
                        )
                        jobs.append(
                            Job(
                                id=item.get("id"),
                                title=item.get("text"),
                                company=company_name,
                                source="lever",
                                location=loc_text,
                                application_url=item.get("hostedUrl"),
                                posted_at=posted_dt,
                                **_enriched_fields(
                                    item.get("descriptionPlain", ""),
                                    title=item.get("text", ""),
                                ),
                            )
                        )
                    if jobs:
                        return jobs
            except Exception:
                pass

            # 3. Try Ashby
            try:
                if self.source not in (None, "ashby"):
                    raise LookupError("source disabled")
                url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true"
                response = self.http_client.get(url)
                data_dict = response if isinstance(response, dict) else response.json()
                raw_jobs = data_dict.get("jobs", [])
                if raw_jobs:
                    jobs = []
                    for item in raw_jobs:
                        loc_text = item.get("location", "")
                        if not self._is_india_location(loc_text):
                            continue

                        jobs.append(
                            Job(
                                id=item.get("id"),
                                title=item.get("title"),
                                company=company_name,
                                source="ashby",
                                location=loc_text,
                                application_url=item.get("jobUrl"),
                                posted_at=datetime.now(timezone.utc),
                                **_enriched_fields(
                                    item.get("descriptionPlain", ""),
                                    title=item.get("title", ""),
                                ),
                            )
                        )
                    if jobs:
                        return jobs
            except Exception:
                pass

        # 4. Try Workday (Checks manual overrides first, then falls back to generic slug matching)
        if self.source not in (None, "workday"):
            return []

        workday_targets = []
        if norm_name in self.WORKDAY_OVERRIDES:
            workday_targets.append(self.WORKDAY_OVERRIDES[norm_name])
        else:
            for slug in slugs:
                workday_targets.append({"tenant": slug, "site_name": f"{slug}ExternalCareerSite", "tier": "wd5"})
                workday_targets.append({"tenant": slug, "site_name": slug, "tier": "wd5"})

        for target in workday_targets:
            tenant = target["tenant"]
            site_name = target["site_name"]
            base_tier = target["tier"]
            tiers = [base_tier, "wd1", "wd3", "wd5"]

            for tier in set(tiers):
                try:
                    url = f"https://{tenant}.{tier}.myworkdayjobs.com/wday/cxs/{tenant}/{site_name}/jobs"
                    headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                    # Passing "India" in searchText or facets helps narrow down Workday listings server-side
                    payload = {
                        "limit": 20,
                        "offset": 0,
                        "appliedFacets": {},
                        "searchText": "India"
                    }
                    
                    response = self.http_client.post(url, json=payload, headers=headers)
                    data = response if isinstance(response, dict) else response.json()
                    job_postings = data.get("jobPostings", [])
                    
                    if job_postings:
                        jobs = []
                        for item in job_postings:
                            loc_text = item.get("locationsText", "")
                            if not self._is_india_location(loc_text):
                                continue

                            application_url = f"https://{tenant}.{tier}.myworkdayjobs.com{item.get('externalPath')}"
                            try:
                                detail_url = (
                                    f"https://{tenant}.{tier}.myworkdayjobs.com/"
                                    f"wday/cxs/{tenant}/{site_name}"
                                    f"{item.get('externalPath')}"
                                )
                                detail_response = self.http_client.get(
                                    detail_url,
                                    headers=headers,
                                )
                                detail_description = description_from_response(
                                    detail_response
                                )
                                retrieval_status = None
                            except Exception:
                                detail_description = ""
                                retrieval_status = "retrieval_failed"
                            jobs.append(
                                Job(
                                    id=str(item.get("bulletFields", [item.get("externalPath")])[0]),
                                    title=item.get("title"),
                                    company=company_name,
                                    source="workday",
                                    location=loc_text,
                                    application_url=application_url,
                                    posted_at=parse_relative_posted_date(
                                        item.get("postedOn", item.get("posted", ""))
                                    ),
                                    **_enriched_fields(
                                        detail_description,
                                        title=item.get("title", ""),
                                        retrieval_status=retrieval_status,
                                    ),
                                )
                            )
                        if jobs:
                            return jobs
                except Exception:
                    continue
                
        return []

    def collect_all(self) -> list[Job]:
        all_jobs = []
        print(f"Racing ATS endpoints for {len(self.companies)} companies concurrently (India filter active)...")
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_company = {
                executor.submit(self._probe_company, company): company 
                for company in self.companies
            }

            for future in as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    jobs = future.result()
                    if jobs:
                        self._record_stat("companies_with_jobs")

                        print(
                            f"  -> Found {len(jobs)} India jobs for {company}"
                        )

                        all_jobs.extend(jobs)

                    else:
                        self._record_stat("companies_no_jobs")
                except Exception:
                    pass

        print("\n" + "=" * 70)
        print("ATS COLLECTION SUMMARY")
        print("=" * 70)

        print(f"Companies scanned : {len(self.companies)}")
        print(f"Companies with jobs : {self.stats['companies_with_jobs']}")
        print(f"Companies with no jobs : {self.stats['companies_no_jobs']}")
        print(f"Total jobs collected : {len(all_jobs)}")

        print("=" * 70)

        return all_jobs
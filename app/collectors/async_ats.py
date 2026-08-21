from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from app.collectors.india_registry import IndiaCompanyRegistry, SourceType, CompanyConfig
from app.collectors.greenhouse import GreenhouseCollector
from app.models.job import Job
from app.services.http_client import HTTPClient

class AsyncMultiATSCollector:
    """Blazing fast parallel collector that scrapes all ATS platforms concurrently."""

    # Explicit manual overrides for Workday enterprises whose routes differ from standard slugs
    WORKDAY_OVERRIDES = {
        "workday": {"tenant": "workday", "site_name": "Workday", "tier": "wd5"},
        "adobe": {"tenant": "adobe", "site_name": "adobe", "tier": "wd5"},
        "netflix": {"tenant": "netflix", "site_name": "netflix", "tier": "wd1"},
    }

    def __init__(self, registry: IndiaCompanyRegistry, http_client: HTTPClient, max_workers: int = 15):
        self.registry = registry
        self.http_client = http_client
        self.max_workers = max_workers

    def _fetch_company_jobs(self, company: CompanyConfig) -> list[Job]:
        """Worker function to fetch jobs for a single company."""
        try:
            if company.source_type == SourceType.GREENHOUSE:
                token = company.config_params.get("board_token", company.id)
                collector = GreenhouseCollector(
                    company=company.name,
                    board_token=token,
                    http_client=self.http_client,
                )
                return collector.collect()

            elif company.source_type == SourceType.LEVER:
                token = company.config_params.get("board_token", company.id)
                url = f"https://api.lever.co/v0/postings/{token}?mode=json"
                response = self.http_client.get(url)
                data = response if isinstance(response, list) else response.json()
                
                jobs = []
                for item in data:
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
                            company=company.name,
                            source="lever",
                            location=item.get("categories", {}).get("location", "India"),
                            application_url=item.get("hostedUrl"),
                            posted_at=posted_dt,
                            description=item.get("descriptionPlain", ""),
                        )
                    )
                return jobs

            elif company.source_type == SourceType.ASHBY:
                token = company.config_params.get("board_token", company.id)
                url = f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"
                response = self.http_client.get(url)
                data_dict = response if isinstance(response, dict) else response.json()
                raw_jobs = data_dict.get("jobs", [])
                
                jobs = []
                for item in raw_jobs:
                    jobs.append(
                        Job(
                            id=item.get("id"),
                            title=item.get("title"),
                            company=company.name,
                            source="ashby",
                            location=item.get("location", "India"),
                            application_url=item.get("jobUrl"),
                            posted_at=datetime.now(timezone.utc),
                            description=item.get("descriptionPlain", ""),
                        )
                    )
                return jobs

            elif company.source_type == SourceType.WORKDAY:
                norm_id = company.id.lower().strip()
                
                # 1. Check if we have an explicit override mapping for this enterprise
                if norm_id in self.WORKDAY_OVERRIDES:
                    override = self.WORKDAY_OVERRIDES[norm_id]
                    tenants_to_try = [override]
                else:
                    # 2. Fallback dynamic permutations based on plain-text ID
                    slug = norm_id.replace(" ", "").replace(".", "").replace("-", "")
                    tenants_to_try = [
                        {"tenant": slug, "site_name": f"{slug}ExternalCareerSite", "tier": "wd5"},
                        {"tenant": slug, "site_name": slug, "tier": "wd5"}
                    ]

                for target in tenants_to_try:
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
                            
                            payload = {
                                "limit": 20,
                                "offset": 0,
                                "appliedFacets": {},
                                "searchText": ""
                            }
                            
                            response = self.http_client.post(url, json=payload, headers=headers)
                            data = response if isinstance(response, dict) else response.json()
                            job_postings = data.get("jobPostings", [])
                            
                            if job_postings:
                                jobs = []
                                for item in job_postings:
                                    jobs.append(
                                        Job(
                                            id=str(item.get("bulletFields", [item.get("externalPath")])[0]),
                                            title=item.get("title"),
                                            company=company.name,
                                            source="workday",
                                            location=item.get("locationsText", "India"),
                                            application_url=f"https://{tenant}.{tier}.myworkdayjobs.com{item.get('externalPath')}",
                                            posted_at=datetime.now(timezone.utc),
                                            description="",
                                        )
                                    )
                                return jobs
                        except Exception:
                            continue
                return []

        except Exception as e:
            return []
        return []

    def collect_all(self) -> list[Job]:
        """Dispatches all companies across a thread pool for parallel execution."""
        all_jobs = []
        companies = self.registry.get_active_india()
        
        print(f"Launching parallel collection for {len(companies)} companies using {self.max_workers} threads...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_company = {
                executor.submit(self._fetch_company_jobs, company): company 
                for company in companies
            }

            for future in as_completed(future_to_company):
                company = future_to_company[future]
                try:
                    jobs = future.result()
                    if jobs:
                        print(f"  -> {company.name:<15} -> {len(jobs):>5} jobs")
                        all_jobs.extend(jobs)
                except Exception as exc:
                    pass

        return all_jobs
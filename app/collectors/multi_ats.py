from datetime import datetime, timezone
from app.collectors.india_registry import IndiaCompanyRegistry, SourceType, CompanyConfig
from app.collectors.greenhouse import GreenhouseCollector
from app.models.job import Job
from app.services.http_client import HTTPClient

class MultiATSCollector:
    """Unified collector for Greenhouse, Lever, Ashby, and Workday job boards."""

    # Explicit manual overrides for Workday enterprises whose routes differ from standard slugs
    WORKDAY_OVERRIDES = {
        "workday": {"tenant": "workday", "site_name": "Workday", "tier": "wd5"},
        "adobe": {"tenant": "adobe", "site_name": "adobe", "tier": "wd5"},
        "netflix": {"tenant": "netflix", "site_name": "netflix", "tier": "wd1"},
    }

    def __init__(self, registry: IndiaCompanyRegistry, http_client: HTTPClient):
        self.registry = registry
        self.http_client = http_client

    def collect_all(self) -> list[Job]:
        all_jobs = []
        companies = self.registry.get_active_india()
        
        for company in companies:
            print(f"Collecting from {company.name} ({company.source_type.value})...")
            try:
                if company.source_type == SourceType.GREENHOUSE:
                    jobs = self._collect_greenhouse(company)
                elif company.source_type == SourceType.LEVER:
                    jobs = self._collect_lever(company)
                elif company.source_type == SourceType.ASHBY:
                    jobs = self._collect_ashby(company)
                elif company.source_type == SourceType.WORKDAY:
                    jobs = self._collect_workday(company)
                else:
                    continue
                
                print(f"  -> {company.name:<15} -> {len(jobs):>5} jobs")
                all_jobs.extend(jobs)
            except Exception as e:
                print(f"  -> Warning: failed to collect {company.name}: {e}")
                
        return all_jobs

    def _collect_greenhouse(self, company: CompanyConfig) -> list[Job]:
        token = company.config_params.get("board_token", company.id)
        collector = GreenhouseCollector(
            company=company.name,
            board_token=token,
            http_client=self.http_client,
        )
        return collector.collect()

    def _collect_lever(self, company: CompanyConfig) -> list[Job]:
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

    def _collect_ashby(self, company: CompanyConfig) -> list[Job]:
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

    def _collect_workday(self, company: CompanyConfig) -> list[Job]:
        tenant = company.config_params.get("tenant", company.id).lower().replace(" ", "")
        site_name = company.config_params.get("site_name", company.config_params.get("board_token", tenant))
        tiers = [company.config_params.get("tier", "wd5"), "wd1", "wd3", "wd5"]
        
        for tier in set(tiers):
            try:
                base_url = f"https://{tenant}.{tier}.myworkdayjobs.com"
                api_url = f"{base_url}/wday/cxs/{tenant}/{site_name}/jobs"
                
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Origin": base_url,
                    "Referer": f"{base_url}/{site_name}",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                }
                
                payload = {
                    "limit": 20,
                    "offset": 0,
                    "appliedFacets": {},
                    "searchText": ""
                }
                
                # Make sure your http_client supports custom headers for POST
                response = self.http_client.post(api_url, json=payload, headers=headers)
                
                # Check if response status or format is valid
                data = response if isinstance(response, dict) else (response.json() if hasattr(response, 'json') else {})
                job_postings = data.get("jobPostings", [])
                
                if job_postings:
                    jobs = []
                    for item in job_postings:
                        # Handle external path safely
                        ext_path = item.get("externalPath", "")
                        bullet_fields = item.get("bulletFields", [])
                        job_id = bullet_fields[0] if bullet_fields else ext_path
                        
                        jobs.append(
                            Job(
                                id=str(job_id),
                                title=item.get("title"),
                                company=company.name,
                                source="workday",
                                location=item.get("locationsText", "India"),
                                application_url=f"{base_url}{ext_path}",
                                posted_at=datetime.now(timezone.utc),
                                description="",
                            )
                        )
                    print(f"  -> Workday Success for {company.name} on {tier} ({len(jobs)} jobs)")
                    return jobs
            except Exception as e:
                # Uncomment during debugging to see why a tier failed:
                # print(f"Debug Workday error for {company.name} on {tier}: {e}")
                continue
        return []
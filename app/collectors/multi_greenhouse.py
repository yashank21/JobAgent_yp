"""
Multi-company Greenhouse collector.

Aggregates jobs from multiple Greenhouse job boards while
isolating failures between individual companies.
"""

from app.collectors.greenhouse import GreenhouseCollector
from app.models.job import Job
from app.services.http_client import HTTPClient


class MultiGreenhouseCollector:
    """Collect jobs from multiple Greenhouse boards."""

    def __init__(
        self,
        companies: list[dict[str, str]],
        http_client: HTTPClient,
    ):
        self.companies = companies
        self.http_client = http_client

    def collect(self) -> list[Job]:
        """
        Collect jobs from all configured companies.

        A failure from one company does not stop collection
        from the remaining companies.
        """

        all_jobs: list[Job] = []

        for config in self.companies:
            company = config["company"]
            board_token = config["board_token"]

            try:
                # Pass positional parameters or exact kwargs expected by GreenhouseCollector
                collector = GreenhouseCollector(
                    company=company,
                    board_token=board_token,
                    http_client=self.http_client,
                )
                jobs = collector.collect()

                # Print explicit distribution diagnostic
                print(f"{company:<15} -> {len(jobs):>5} jobs")

            except Exception as exc:
                print(f"Warning: failed to collect {company}: {exc}")
                continue

            all_jobs.extend(jobs)
        return self._deduplicate(all_jobs)

    @staticmethod
    def _deduplicate(
        jobs: list[Job],
    ) -> list[Job]:
        """
        Remove duplicate jobs using source + job ID.
        """

        unique_jobs: list[Job] = []
        seen: set[tuple[str, str]] = set()

        for job in jobs:

            key = (
                job.source,
                job.id,
            )

            if key in seen:
                continue

            seen.add(key)
            unique_jobs.append(job)

        return unique_jobs
"""
Real JobAgent email digest test.

Runs the existing collection -> ranking pipeline
and emails the top eligible jobs from the last 48 hours.
"""

from app.config.candidate_profile import CANDIDATE_PROFILE
from app.collectors.company_registry import GREENHOUSE_COMPANIES
from app.collectors.greenhouse import GreenhouseCollector
from app.email.email_service import EmailService
from app.scoring.final_scorer import rank_jobs
from app.services.http_client import HTTPClient


def main():
    client = HTTPClient()

    jobs = []

    for company in GREENHOUSE_COMPANIES:
        collector = GreenhouseCollector(
            company["company"],
            company["board_token"],
            client,
        )

        jobs.extend(
            collector.collect()
        )

    print("TOTAL COLLECTED:", len(jobs))

    ranked = rank_jobs(
        CANDIDATE_PROFILE,
        jobs,
    )

    print(
        "ELIGIBLE + RECENT:",
        len(ranked),
    )

    top_jobs = ranked[:5]

    print()
    print("TOP JOBS:")
    print("-" * 80)

    for match in top_jobs:
        print(
            round(match.final_score, 2),
            "|",
            match.job.company,
            "|",
            match.job.title,
            "|",
            match.job.location,
        )

    print("-" * 80)

    email_service = EmailService()

    email_service.send_job_digest(
        top_jobs,
    )

    print()
    print("REAL JOB DIGEST SENT SUCCESSFULLY")


if __name__ == "__main__":
    main()
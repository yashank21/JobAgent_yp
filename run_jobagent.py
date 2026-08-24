"""
JobAgent production runner.

Canonical production pipeline:
companies.txt
    -> UniversalATSRacer
    -> Wellfound
    -> recent-job filtering
    -> ranking
    -> email digest
"""

from app.config.candidate_profile import CANDIDATE_PROFILE
from app.collectors.universal_racer import UniversalATSRacer
from app.collectors.wellfound import WellfoundCollector
from app.email.email_service import EmailService
from app.scoring.job_ranker import rank_jobs
from app.services.http_client import HTTPClient
from app.services.job_filter import filter_recent_jobs
from app.services.recent_job_enricher import (
    enrich_recent_jobs_with_gemini,
)
from app.services.job_deduplicator import deduplicate_jobs

from app.services.company_loader import load_companies_from_file

LOOKBACK_HOURS = 48
TOP_JOBS = 5
MAX_WORKERS = 10





def main() -> None:
    client = HTTPClient()

    # ---------------------------------------------------------
    # 1. Load company registry
    # ---------------------------------------------------------

    company_names = load_companies_from_file()

    print(
        f"Loaded {len(company_names):,} companies "
        "from companies.txt"
    )

    # ---------------------------------------------------------
    # 2. Collect from ATS platforms
    # ---------------------------------------------------------

    print("\nCollecting jobs through Universal ATS Racer...")

    racer = UniversalATSRacer(
        companies=company_names,
        http_client=client,
        max_workers=MAX_WORKERS,
    )

    ats_jobs = racer.collect_all()

    print(
        f"ATS jobs collected: {len(ats_jobs):,}"
    )

    # ---------------------------------------------------------
    # 3. Collect Wellfound
    # ---------------------------------------------------------

    print("\nCollecting jobs from Wellfound...")

    wellfound_collector = WellfoundCollector(
        http_client=client,
    )

    wellfound_jobs = wellfound_collector.collect()

    print(
        f"Wellfound jobs collected: "
        f"{len(wellfound_jobs):,}"
    )

    # ---------------------------------------------------------
    # 4. Combine sources
    # ---------------------------------------------------------

    all_jobs = ats_jobs + wellfound_jobs

    print(
        f"\nTotal jobs collected: "
        f"{len(all_jobs):,}"
    )

    # ---------------------------------------------------------
    # 5. Deduplication
    # ---------------------------------------------------------

    all_jobs = deduplicate_jobs(
        all_jobs,
    )

    # ---------------------------------------------------------
    # 5. Freshness filtering
    # ---------------------------------------------------------

    recent_jobs = filter_recent_jobs(
        all_jobs,
        hours=LOOKBACK_HOURS,
    )
    
    import json
    from dataclasses import asdict
    from pathlib import Path

    print(
        f"Jobs from last {LOOKBACK_HOURS} hours: "
        f"{len(recent_jobs):,}"
    )
    
    # ---------------------------------------------------------
    # Save recent jobs for diagnostics
    # ---------------------------------------------------------

    diagnostic_path = Path("data/recent_jobs.json")
    diagnostic_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with diagnostic_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            [
                asdict(job)
                for job in recent_jobs
            ],
            f,
            indent=2,
            default=str,
        )

    print(
        f"Saved {len(recent_jobs):,} recent jobs to "
        f"{diagnostic_path}"
    )
    
    # ---------------------------------------------------------
    # 6. Preliminary ranking
    # ---------------------------------------------------------

    preliminary_matches = rank_jobs(
        CANDIDATE_PROFILE,
        recent_jobs,
        limit=20,
    )

    print(
        f"Preliminary candidates: "
        f"{len(preliminary_matches):,}"
    )

    # ---------------------------------------------------------
    # 7. Gemini semantic enrichment
    # ---------------------------------------------------------

    gemini_jobs = [
        match.job
        for match in preliminary_matches
    ]

    gemini_jobs = enrich_recent_jobs_with_gemini(
        gemini_jobs,
    )

    # ---------------------------------------------------------
    # 8. Final ranking
    # ---------------------------------------------------------

    ranked_jobs = rank_jobs(
        CANDIDATE_PROFILE,
        gemini_jobs,
        limit=TOP_JOBS,
    )

    print(
        f"Top ranked jobs: "
        f"{len(ranked_jobs):,}"
    )

    print(
        f"Top ranked jobs: "
        f"{len(ranked_jobs):,}"
    )

    print("\nTOP JOBS")
    print("=" * 100)

    for match in ranked_jobs:
        print(
            f"\n{match.job.company} | "
            f"{match.job.title}"
        )

        print(
            f"Final Score : {match.final_score:.2f}"
        )

        print(
            f"Role        : {match.role_score:.2f}"
        )

        print(
            f"Skills      : {match.skill_score:.2f}"
        )

        print(
            f"Experience  : {match.experience_score:.2f}"
        )

        print(
            f"Location    : {match.location_score:.2f}"
        )

        print(
            f"Eligible    : {match.eligible}"
        )

        print(
            f"Location    : {match.job.location}"
        )

        print("-" * 100)


    # ---------------------------------------------------------
    # 7. Email digest
    # ---------------------------------------------------------

    if not ranked_jobs:
        print(
            "\nNo eligible jobs found. "
            "Digest will not be sent."
        )
        return

    email_service = EmailService()

    email_service.send_job_digest(
        ranked_jobs,
    )

    print(
        "\nJOBAGENT DIGEST SENT SUCCESSFULLY"
    )


if __name__ == "__main__":
    main()

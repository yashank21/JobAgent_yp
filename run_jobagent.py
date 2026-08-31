"""
JobAgent production runner.

Canonical production pipeline:
    resume + explicit user preferences
        -> collect jobs
        -> recent-job filtering
        -> ranking
        -> email digest

This runner is candidate-agnostic. Nothing in ranking is
hardcoded to a specific person.
"""
import argparse
from dataclasses import asdict
from pathlib import Path
import json

from app.models.candidate import CandidateProfile
from app.services.resume_parser import extract_resume_text
from app.services.candidate_profile_builder import (
    build_candidate_profile,
)
from app.collectors.universal_racer import UniversalATSRacer
from app.collectors.wellfound import (
    WellfoundCollector,
    wellfound_search_urls,
)
from app.email.email_service import EmailService
from app.scoring.job_ranker import rank_jobs
from app.scoring.explanation import explain_match
from app.services.http_client import HTTPClient
from app.services.job_filter import filter_recent_jobs
from app.services.recent_job_enricher import (
    enrich_recent_jobs_with_groq,
)
from app.services.job_deduplicator import deduplicate_jobs
from app.services.company_loader import load_companies_from_file

LOOKBACK_HOURS = 48
TOP_JOBS = 10
MAX_WORKERS = 10


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run JobAgent"
    )

    parser.add_argument(
        "--resume",
        required=True,
        help="Path to the user's resume PDF or DOCX",
    )

    return parser.parse_args()


def _split_csv(raw: str) -> list[str]:
    return [
        item.strip()
        for item in raw.split(",")
        if item.strip()
    ]


def collect_explicit_preferences(
    profile: CandidateProfile,
) -> CandidateProfile:
    """
    Ask the current user for intent. Resume facts stay as-is.
    """

    print("\nWhat primary roles are you targeting?")
    print("Enter roles separated by commas.")
    print("Example: AI Engineer, Backend Engineer")

    primary = _split_csv(input("\nPrimary roles: ").strip())

    if primary:
        profile.preferred_roles = primary
    elif profile.resume_roles:
        profile.preferred_roles = list(profile.resume_roles)
        print(
            "No primary roles entered. "
            "Resume-derived roles will be used as intent."
        )
    else:
        print(
            "No primary roles entered and none were found "
            "on the resume. Role ranking will be weak."
        )

    print("\nAny secondary / acceptable roles? (optional)")
    secondary = _split_csv(input("Secondary roles: ").strip())
    if secondary:
        profile.secondary_roles = secondary

    print("\nPreferred locations? (optional)")
    print("Example: India, Bengaluru, Remote")
    locations = _split_csv(input("Locations: ").strip())
    if locations:
        profile.preferred_locations = locations

    print("\nMinimum salary in LPA? (optional, press Enter to skip)")
    salary_raw = input("Minimum LPA: ").strip()
    if salary_raw:
        try:
            profile.minimum_salary_lpa = float(salary_raw)
        except ValueError:
            print("Could not parse salary. Leaving it unset.")

    return profile


def main(resume_path: str) -> None:
    client = HTTPClient()

    print("\nLoading candidate resume...")

    resume_text = extract_resume_text(resume_path)

    # Always start from a blank profile so a previous user's
    # preferences cannot leak into this run.
    candidate_profile = build_candidate_profile(
        resume_text,
        base_profile=CandidateProfile(),
    )

    print(f"\nResume loaded: {resume_path}")
    print(f"Resume skills: {len(candidate_profile.skills):,}")
    print(f"Resume roles: {candidate_profile.resume_roles}")
    print(
        f"Experience: "
        f"{candidate_profile.experience_years:.2f} years"
    )
    print(f"Career level: {candidate_profile.career_level}")

    if candidate_profile.resume_roles:
        print("\nRoles inferred from the resume:")
        for role in candidate_profile.resume_roles:
            print(f"  - {role}")

    candidate_profile = collect_explicit_preferences(
        candidate_profile,
    )

    print("\nUsing profile intent:")
    print(f"  Primary roles: {candidate_profile.preferred_roles}")
    print(f"  Secondary roles: {candidate_profile.secondary_roles}")
    print(
        f"  Locations: {candidate_profile.preferred_locations}"
    )
    print(
        f"  Minimum salary LPA: "
        f"{candidate_profile.minimum_salary_lpa}"
    )

    company_names = load_companies_from_file()

    print(
        f"\nLoaded {len(company_names):,} companies "
        "from companies.txt"
    )

    print("\nCollecting jobs through Universal ATS Racer...")

    racer = UniversalATSRacer(
        companies=company_names,
        http_client=client,
        max_workers=MAX_WORKERS,
    )

    ats_jobs = racer.collect_all()

    print(f"ATS jobs collected: {len(ats_jobs):,}")

    print("\nCollecting jobs from Wellfound...")

    wellfound_urls = wellfound_search_urls(
        roles=(
            candidate_profile.preferred_roles
            + candidate_profile.secondary_roles
        ),
        locations=candidate_profile.preferred_locations,
    )

    print("Wellfound search URLs:")
    for url in wellfound_urls:
        print(f"  {url}")

    wellfound_collector = WellfoundCollector(
        http_client=client,
        urls=wellfound_urls,
    )

    wellfound_jobs = wellfound_collector.collect()

    print(
        f"Wellfound jobs collected: "
        f"{len(wellfound_jobs):,}"
    )

    all_jobs = deduplicate_jobs(ats_jobs + wellfound_jobs)

    print(f"\nTotal jobs collected: {len(all_jobs):,}")

    recent_jobs = filter_recent_jobs(
        all_jobs,
        hours=LOOKBACK_HOURS,
    )

    print(
        f"Jobs from last {LOOKBACK_HOURS} hours: "
        f"{len(recent_jobs):,}"
    )

    diagnostic_path = Path("data/recent_jobs.json")
    diagnostic_path.parent.mkdir(parents=True, exist_ok=True)

    with diagnostic_path.open("w", encoding="utf-8") as f:
        json.dump(
            [asdict(job) for job in recent_jobs],
            f,
            indent=2,
            default=str,
        )

    print(
        f"Saved {len(recent_jobs):,} recent jobs to "
        f"{diagnostic_path}"
    )

    groq_jobs = enrich_recent_jobs_with_groq(recent_jobs)

    print(f"Enriched candidates: {len(groq_jobs):,}")

    ranked_jobs = rank_jobs(
        candidate_profile,
        groq_jobs,
        limit=TOP_JOBS,
    )

    print(f"Top ranked jobs: {len(ranked_jobs):,}")

    print("\nTOP JOBS")
    print("=" * 100)

    for match in ranked_jobs:
        print(f"\n{match.job.company} | {match.job.title}")
        print(f"Final Score : {match.final_score:.2f}")
        print(f"Role        : {match.role_score:.2f}")
        print(f"Skills      : {match.skill_score:.2f}")
        print(f"Experience  : {match.experience_score:.2f}")
        print(f"Location    : {match.location_score:.2f}")
        print(f"Eligible    : {match.eligible}")
        print(f"Job location: {match.job.location}")

        explanations = explain_match(
            candidate_profile,
            match.job,
        )
        for line in explanations[:8]:
            print(f"  {line}")

        print("-" * 100)

    if not ranked_jobs:
        print(
            "\nNo eligible jobs found. "
            "Digest will not be sent."
        )
        return

    email_service = EmailService()

    email_service.send_job_digest(ranked_jobs)

    print("\nJOBAGENT DIGEST SENT SUCCESSFULLY")


if __name__ == "__main__":
    args = parse_args()
    main(args.resume)

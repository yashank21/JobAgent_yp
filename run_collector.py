from collections import Counter
from datetime import datetime, timezone

from app.collectors.company_registry import GREENHOUSE_COMPANIES
from app.collectors.multi_greenhouse import MultiGreenhouseCollector
from app.collectors.wellfound import WellfoundCollector
from app.config.candidate_profile import CANDIDATE_PROFILE
from app.eligibility.eligibility import check_eligibility
from app.scoring.explanation import explain_match
from app.scoring.job_ranker import rank_jobs
from app.services.http_client import HTTPClient
from app.services.job_filter import filter_recent_jobs


LOOKBACK_HOURS = 48
TOP_JOBS = 10


def classify_reason(reason: str) -> str:
    """
    Convert a human-readable eligibility reason
    into a compact diagnostic category.
    """

    text = reason.lower()

    if (
        "authorization" in text
        or "itar" in text
        or "citizen" in text
        or "permanent resident" in text
        or "green card" in text
    ):
        return "Work authorization restriction"

    if "outside preferred locations" in text:
        return "Location mismatch"

    if (
        "years" in text
        and (
            "require" in text
            or "experience" in text
        )
    ):
        return "Experience mismatch"

    if "preferred roles" in text:
        return "Role mismatch"

    if "job role" in text:
        return "Role mismatch"

    if reason.startswith("Location"):
        return "Location mismatch"

    if reason.startswith("Requires"):
        return "Experience mismatch"

    if reason.startswith("Work authorization"):
        return "Work authorization restriction"

    return reason


def print_newest_jobs(
    jobs,
    limit=10,
):
    """
    Print the newest jobs returned across collectors.

    Useful for debugging timestamp and filtering issues.
    """

    print()
    print("=" * 80)
    print(f"{limit} NEWEST JOBS RETURNED")
    print("=" * 80)

    now = datetime.now(timezone.utc)

    sorted_jobs = sorted(
        jobs,
        key=lambda job: job.posted_at
        or datetime.min.replace(
            tzinfo=timezone.utc
        ),
        reverse=True,
    )

    for job in sorted_jobs[:limit]:

        if job.posted_at is None:
            age = "unknown"

        else:
            posted_at = job.posted_at

            if posted_at.tzinfo is None:
                posted_at = posted_at.replace(
                    tzinfo=timezone.utc
                )

            age = (
                f"{(
                    now - posted_at
                ).total_seconds() / 3600:.2f} hours"
            )

        print()
        print(f"Title: {job.title}")
        print(f"Company: {job.company}")
        print(f"Source: {getattr(job, 'source', 'N/A')}")
        print(f"Posted: {job.posted_at}")
        print(f"Age: {age}")
        print(f"Location: {job.location}")
        print(f"URL: {job.application_url or getattr(job, 'source_url', '')}")


def print_eligibility_diagnostics(
    candidate,
    jobs,
):
    """
    Print a diagnostic summary showing why recent
    jobs were accepted or rejected.
    """

    print()
    print("=" * 80)
    print("ELIGIBILITY DIAGNOSTICS")
    print("=" * 80)

    if not jobs:
        print()
        print("No recent jobs to evaluate.")
        print("-" * 80)
        return

    reason_counts = Counter()
    eligible_jobs = []
    job_results = []

    for job in jobs:

        result = check_eligibility(
            candidate,
            job,
        )

        job_results.append(
            (job, result)
        )

        if getattr(result, "eligible", getattr(result, "is_eligible", False)):
            eligible_jobs.append(job)

        else:
            for reason in result.reasons:
                reason_counts[
                    classify_reason(reason)
                ] += 1

    print()
    print(
        f"Recent jobs evaluated: {len(jobs)}"
    )

    print(
        f"Eligible jobs:         "
        f"{len(eligible_jobs)}"
    )

    print(
        f"Rejected jobs:         "
        f"{len(jobs) - len(eligible_jobs)}"
    )

    # -----------------------------------------
    # Rejection reasons
    # -----------------------------------------

    print()
    print("REJECTION REASONS")
    print("-" * 80)

    if not reason_counts:
        print("  None")

    else:
        for reason, count in reason_counts.most_common():
            print(
                f"  {count:>3}x  {reason}"
            )

    # -----------------------------------------
    # Job-level results
    # -----------------------------------------

    print()
    print("JOB-LEVEL RESULTS")
    print("-" * 80)

    for job, result in job_results:

        is_elig = getattr(result, "eligible", getattr(result, "is_eligible", False))
        status = (
            "ELIGIBLE"
            if is_elig
            else "REJECTED"
        )

        print()
        print(
            f"[{status}] {job.title}"
        )

        print(
            f"  Company:  {job.company}"
        )

        print(
            f"  Location: {job.location}"
        )

        if result.reasons:

            for reason in result.reasons:
                print(
                    f"  ✗ {reason}"
                )

        else:
            print(
                "  ✓ Passed all hard eligibility checks"
            )

    print()
    print("-" * 80)


def print_ranked_jobs(
    candidate,
    ranked_jobs,
):
    """
    Print final ranked eligible jobs with explanations.
    """

    print()
    print("=" * 80)
    print("TOP JOB MATCHES")
    print("=" * 80)

    if not ranked_jobs:
        print()
        print(
            "No eligible jobs found "
            "in the selected time window."
        )
        return

    for index, item in enumerate(
        ranked_jobs,
        start=1,
    ):
        # Handle tuple (job, score) or MatchResult object
        if isinstance(item, tuple):
            job, score = item
            match_obj = None
        else:
            job = item.job
            score = item.score * 100 if item.score <= 1.0 else item.score
            match_obj = item

        print()
        print(
            f"#{index} {job.title}"
        )

        print(
            f"Company: {job.company}"
        )

        print(
            f"Location: {job.location}"
        )

        print(
            f"Match Score: {score}%"
        )

        print(
            f"Posted: {job.posted_at}"
        )

        print(
            f"URL: {job.application_url or getattr(job, 'source_url', '')}"
        )

        print(
            f"Required skills: "
            f"{job.required_skills}"
        )

        print(
            f"Preferred skills: "
            f"{job.preferred_skills}"
        )

        # -----------------------------------------
        # Match explanation
        # -----------------------------------------

        print()
        print("WHY THIS JOB MATCHES:")

        explanations = explain_match(
            candidate,
            match_obj if match_obj else job,
        )

        for explanation in explanations:
            print(
                f"  {explanation}"
            )

        print("-" * 80)


def main():

    client = HTTPClient()

    # -----------------------------------------
    # Multi-company Greenhouse collector
    # -----------------------------------------

    greenhouse_collector = MultiGreenhouseCollector(
        companies=GREENHOUSE_COMPANIES,
        http_client=client,
    )

    # -----------------------------------------
    # Wellfound collector
    # -----------------------------------------

    wellfound_collector = WellfoundCollector(
        http_client=client,
    )

    # -----------------------------------------
    # Single source-of-truth candidate profile
    # -----------------------------------------

    candidate = CANDIDATE_PROFILE

    print(
        "Collecting jobs from Greenhouse..."
    )
    greenhouse_jobs = greenhouse_collector.collect()

    print(
        "Collecting jobs from Wellfound..."
    )
    wellfound_jobs = wellfound_collector.collect()

    # Combine both datasets
    jobs = greenhouse_jobs + wellfound_jobs

    print(
        f"Greenhouse jobs collected: {len(greenhouse_jobs)}"
    )
    print(
        f"Wellfound jobs collected:  {len(wellfound_jobs)}"
    )
    print(
        f"Total jobs collected:     {len(jobs)}"
    )

    print(
        f"Current UTC: "
        f"{datetime.now(timezone.utc)}"
    )

    # -----------------------------------------
    # Diagnostic: newest jobs
    # -----------------------------------------

    print_newest_jobs(
        jobs,
        limit=10,
    )

    # -----------------------------------------
    # Recent jobs
    # -----------------------------------------

    recent_jobs = filter_recent_jobs(
        jobs,
        hours=LOOKBACK_HOURS,
    )

    print()
    print("=" * 80)
    print(
        f"Jobs posted in the last "
        f"{LOOKBACK_HOURS} hours: "
        f"{len(recent_jobs)}"
    )
    print("=" * 80)

    # 1. Print diagnostics
    print_eligibility_diagnostics(
        candidate,
        recent_jobs,
    )

    # 2. Filter out ineligible jobs BEFORE ranking
    eligible_jobs = [
        job for job in recent_jobs 
        if check_eligibility(candidate, job).eligible
    ]

    # 3. Pass ONLY eligible jobs to rank_jobs
    ranked_jobs = rank_jobs(
        candidate,
        eligible_jobs,
        limit=TOP_JOBS,
    )

    # -----------------------------------------
    # Final output
    # -----------------------------------------

    print_ranked_jobs(
        candidate,
        ranked_jobs,
    )


if __name__ == "__main__":
    main()
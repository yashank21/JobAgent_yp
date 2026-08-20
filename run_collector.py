from collections import Counter
from datetime import datetime, timezone
import sys

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

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

# Set True only when you want every rejected job printed.
VERBOSE_REJECTIONS = False


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
        print(
            f"URL: "
            f"{job.application_url or getattr(job, 'source_url', '')}"
        )


def print_eligibility_diagnostics(
    candidate,
    jobs,
    verbose=True,
):
    """
    Print compact eligibility diagnostics.

    By default this prints only aggregate statistics.
    Set verbose=True to print every rejected job.
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

        is_eligible = getattr(
            result,
            "eligible",
            getattr(result, "is_eligible", False),
        )

        job_results.append(
            (job, result)
        )

        if is_eligible:
            eligible_jobs.append(job)

        else:
            for reason in result.reasons:
                reason_counts[
                    classify_reason(reason)
                ] += 1

    rejected_jobs = len(jobs) - len(eligible_jobs)

    # -----------------------------------------
    # Summary
    # -----------------------------------------

    print()
    print(
        f"Recent jobs evaluated: {len(jobs):,}"
    )

    print(
        f"Eligible jobs:         {len(eligible_jobs):,}"
    )

    print(
        f"Rejected jobs:         {rejected_jobs:,}"
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
            percentage = (
                count / len(jobs) * 100
            )

            print(
                f"  {count:>5,}x  "
                f"{reason:<40} "
                f"({percentage:5.1f}%)"
            )

    # -----------------------------------------
    # Optional detailed output
    # -----------------------------------------

    if verbose:

        print()
        print("JOB-LEVEL RESULTS")
        print("-" * 80)

        for job, result in job_results:

            is_eligible = getattr(
                result,
                "eligible",
                getattr(result, "is_eligible", False),
            )

            status = (
                "ELIGIBLE"
                if is_eligible
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
                        f"  [REJECTED] {reason}"
                    )

            else:
                print(
                    "  [PASSED] Passed all hard eligibility checks"
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

    for index, match in enumerate(
        ranked_jobs,
        start=1,
    ):

        job = match.job

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
            f"Match Score: {match.final_score}%"
        )

        print(
            f"Posted: {job.posted_at}"
        )

        print(
            f"URL: "
            f"{job.application_url or getattr(job, 'source_url', '')}"
        )

        print(
            f"Required skills: "
            f"{job.required_skills}"
        )

        print(
            f"Preferred skills: "
            f"{job.preferred_skills}"
        )

        print()
        print("SCORE BREAKDOWN:")

        print(
            f"  Skill:       {match.skill_score}%"
        )

        print(
            f"  Role:        {match.role_score}%"
        )

        print(
            f"  Experience:  {match.experience_score}%"
        )

        print(
            f"  Location:    {match.location_score}%"
        )

        print()
        print("WHY THIS JOB MATCHES:")

        explanations = explain_match(
            candidate,
            job,
        )

        for explanation in explanations:
            print(
                f"  {explanation}"
            )

        print("-" * 80)


def print_location_summary(jobs):
    """
    Print location distribution for recent jobs.

    Useful for debugging location filtering.
    """

    if not jobs:
        return

    print()
    print("LOCATION DISTRIBUTION")
    print("-" * 80)

    location_counts = Counter(
        job.location
        for job in jobs
    )

    for location, count in location_counts.most_common(30):
        print(
            f"{str(location):<50} -> {count}"
        )


def main():

    client = HTTPClient()

    # -----------------------------------------
    # Collectors
    # -----------------------------------------

    greenhouse_collector = MultiGreenhouseCollector(
        companies=GREENHOUSE_COMPANIES,
        http_client=client,
    )

    wellfound_collector = WellfoundCollector(
        http_client=client,
    )

    # -----------------------------------------
    # Candidate profile
    # -----------------------------------------

    candidate = CANDIDATE_PROFILE

    # -----------------------------------------
    # Collect jobs
    # -----------------------------------------

    print(
        "Collecting jobs from Greenhouse..."
    )

    greenhouse_jobs = (
        greenhouse_collector.collect()
    )

    print(
        "Collecting jobs from Wellfound..."
    )

    wellfound_jobs = (
        wellfound_collector.collect()
    )

    # Combine both datasets
    jobs = (
        greenhouse_jobs
        + wellfound_jobs
    )

    print()
    print(
        f"Greenhouse jobs collected: {len(greenhouse_jobs):,}"
    )

    print(
        f"Wellfound jobs collected:  {len(wellfound_jobs):,}"
    )

    print(
        f"Total jobs collected:      {len(jobs):,}"
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
    # Filter recent jobs
    # -----------------------------------------

        # -----------------------------------------
    # Recent jobs
    # -----------------------------------------

    recent_jobs = filter_recent_jobs(
        jobs,
        hours=LOOKBACK_HOURS,
    )

    print()
    print("=" * 80)
    print("RECENT JOB FILTER")
    print("=" * 80)

    print(
        f"Lookback window: {LOOKBACK_HOURS} hours"
    )

    print(
        f"Jobs before filtering: {len(jobs):,}"
    )

    print(
        f"Jobs in recent window: {len(recent_jobs):,}"
    )

    # -----------------------------------------
    # Location distribution
    # -----------------------------------------

    print()
    print("LOCATION DISTRIBUTION")
    print("-" * 80)

    location_counts = Counter(
        job.location
        for job in recent_jobs
    )

    for location, count in location_counts.most_common(30):
        print(
            f"{str(location):<50} -> {count}"
        )

    # -----------------------------------------
    # Eligibility diagnostics
    # -----------------------------------------

    print_eligibility_diagnostics(
        candidate,
        recent_jobs,
    )

    # -----------------------------------------
    # Rank recent jobs
    # -----------------------------------------

    ranked_jobs = rank_jobs(
        candidate,
        recent_jobs,
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
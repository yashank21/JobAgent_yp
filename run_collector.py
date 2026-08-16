from datetime import datetime, timezone

from app.collectors.greenhouse import GreenhouseCollector
from app.models.candidate import CandidateProfile
from app.scoring.explanation import explain_match
from app.scoring.job_ranker import rank_jobs
from app.services.http_client import HTTPClient
from app.services.job_filter import filter_recent_jobs


LOOKBACK_HOURS = 48
TOP_JOBS = 10


def build_candidate() -> CandidateProfile:
    """
    Build the candidate profile used by the matching pipeline.
    """

    return CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",

        preferred_roles=[
            "Software Engineer",
            "Machine Learning Engineer",
            "Data Engineer",
            "Backend Engineer",
        ],

        preferred_locations=[
            "India",
            "Remote",
        ],

        minimum_salary_lpa=10.0,

        # 11 months internship ≈ 0.92 years
        experience_years=0.92,

        skills=[
            "Python",
            "C++",
            "SQL",
            "Machine Learning",
            "PyTorch",
            "TensorFlow",
            "FastAPI",
            "React",
            "Linux",
        ],
    )


def print_newest_jobs(jobs, limit=10):
    """
    Print the newest jobs returned by Greenhouse.
    Useful for debugging timestamp/filtering issues.
    """

    print()
    print("=" * 80)
    print(f"{limit} NEWEST JOBS RETURNED BY GREENHOUSE")
    print("=" * 80)

    now = datetime.now(timezone.utc)

    sorted_jobs = sorted(
        jobs,
        key=lambda job: job.posted_at or datetime.min.replace(
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
        print(f"Posted: {job.posted_at}")
        print(f"Age: {age}")
        print(f"Location: {job.location}")
        print(f"URL: {job.application_url}")


def print_ranked_jobs(
    candidate,
    ranked_jobs,
):
    """
    Print final ranked jobs with explanations.
    """

    print()
    print("=" * 80)
    print("TOP JOB MATCHES")
    print("=" * 80)

    if not ranked_jobs:
        print()
        print("No eligible jobs found in the selected time window.")
        return

    for index, (job, score) in enumerate(
        ranked_jobs,
        start=1,
    ):

        print()
        print(f"#{index} {job.title}")
        print(f"Company: {job.company}")
        print(f"Location: {job.location}")
        print(f"Match Score: {score}%")
        print(f"Posted: {job.posted_at}")
        print(f"URL: {job.application_url}")

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
            job,
        )

        for explanation in explanations:
            print(f"  {explanation}")

        print("-" * 80)


def main():

    client = HTTPClient()

    collector = GreenhouseCollector(
        company="SpaceX",
        board_token="spacex",
        http_client=client,
    )

    candidate = build_candidate()

    print("Collecting jobs from Greenhouse...")

    jobs = collector.collect()

    print(
        f"Total jobs collected: {len(jobs)}"
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

    # -----------------------------------------
    # Ranking
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
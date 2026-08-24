"""
Semantic enrichment for jobs that survived freshness filtering.

Gemini is intentionally called here instead of during collection so
we do not waste API calls on stale jobs.

The free Gemini tier is rate-limited, so requests are throttled
and 429 failures are handled safely.
"""

import time

from app.services.job_enrichment import enrich_job_description


# Gemini free tier currently allows roughly 5 requests/minute.
# Keep a small safety margin.
GEMINI_REQUEST_INTERVAL = 13.0


def enrich_recent_jobs_with_gemini(
    jobs: list,
) -> list:
    """
    Run Gemini enrichment on recent jobs.

    Requests are deliberately throttled to avoid exceeding the
    Gemini free-tier requests-per-minute quota.

    Jobs without descriptions are skipped.
    Gemini failures never stop the pipeline.
    """

    enriched_jobs = []

    jobs_with_descriptions = [
        job
        for job in jobs
        if (
            getattr(job, "description", "")
            and getattr(job, "description", "").strip()
        )
    ]

    print(
        f"\nRunning Gemini enrichment on "
        f"{len(jobs_with_descriptions):,} jobs..."
    )

    last_request_time = 0.0

    for index, job in enumerate(
        jobs_with_descriptions,
        start=1,
    ):

        description = getattr(
            job,
            "description",
            "",
        )

        title = getattr(
            job,
            "title",
            "",
        )

        # ---------------------------------------------------------
        # Rate limiting
        # ---------------------------------------------------------

        elapsed = time.monotonic() - last_request_time

        if elapsed < GEMINI_REQUEST_INTERVAL:
            sleep_time = (
                GEMINI_REQUEST_INTERVAL - elapsed
            )

            print(
                f"  Waiting {sleep_time:.1f}s "
                f"for Gemini rate limit..."
            )

            time.sleep(sleep_time)

        try:
            enrichment = enrich_job_description(
                description,
                title=title,
                use_gemini=True,
            )

            last_request_time = time.monotonic()

            job.description = enrichment.description

            job.experience_required = (
                enrichment.experience_required
            )

            job.experience_years_required = (
                enrichment.experience_years_required
            )

            job.seniority = (
                enrichment.seniority
            )

            job.role_family = (
                enrichment.role_family
            )

            job.job_type = (
                enrichment.job_type
            )

            job.required_skills = (
                enrichment.required_skills or []
            )

            job.preferred_skills = (
                enrichment.preferred_skills or []
            )

            job.description_status = (
                enrichment.description_status
            )

            job.skills_status = (
                enrichment.skills_status
            )

            job.experience_status = (
                enrichment.experience_status
            )

            job.gemini_confidence = (
                enrichment.gemini_confidence
            )

        except Exception as exc:

            print(
                f"[Gemini] failed for "
                f"{job.company} | {job.title}: "
                f"{type(exc).__name__}: {exc}"
            )

            # Important:
            # A failed Gemini request must not destroy the job.
            # The deterministic extraction already present on
            # the Job object remains usable.

        if (
            index % 5 == 0
            or index == len(jobs_with_descriptions)
        ):
            print(
                f"  Gemini enrichment: "
                f"{index}/{len(jobs_with_descriptions)}"
            )

        enriched_jobs.append(job)

    # Jobs without descriptions are preserved too.
    jobs_without_descriptions = [
        job
        for job in jobs
        if not (
            getattr(job, "description", "")
            and getattr(job, "description", "").strip()
        )
    ]

    enriched_jobs.extend(
        jobs_without_descriptions
    )

    return enriched_jobs
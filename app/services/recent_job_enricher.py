"""
Semantic enrichment for jobs that survived freshness filtering.

Groq is called here instead of during collection so we do not
waste API calls on stale jobs.

Jobs without descriptions are skipped.
Groq failures never stop the pipeline.
Rate limits stop further Groq calls; remaining jobs use
deterministic extraction only.
"""

from app.services.job_enrichment import enrich_job_description


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "429" in text
        or "rate_limit" in text
        or "rate limit" in text
    )


def _apply_enrichment(job, enrichment) -> None:
    job.description = enrichment.description
    job.experience_required = enrichment.experience_required
    job.experience_years_required = (
        enrichment.experience_years_required
    )
    job.seniority = enrichment.seniority
    job.role_family = enrichment.role_family
    job.job_type = enrichment.job_type
    job.required_skills = enrichment.required_skills or []
    job.preferred_skills = enrichment.preferred_skills or []
    job.description_status = enrichment.description_status
    job.skills_status = enrichment.skills_status
    job.experience_status = enrichment.experience_status
    job.ai_confidence = enrichment.ai_confidence


def enrich_recent_jobs_with_groq(
    jobs: list,
) -> list:
    """
    Run Groq enrichment on recent jobs.

    Jobs without descriptions are skipped.

    Groq failures never destroy a job. After a rate limit,
    later jobs are enriched deterministically.
    """

    enriched_jobs = []
    use_ai = True

    jobs_with_descriptions = [
        job
        for job in jobs
        if (
            getattr(job, "description", "")
            and getattr(job, "description", "").strip()
        )
    ]

    print(
        f"\nRunning Groq enrichment on "
        f"{len(jobs_with_descriptions):,} jobs..."
    )

    for index, job in enumerate(
        jobs_with_descriptions,
        start=1,
    ):
        description = getattr(job, "description", "")
        title = getattr(job, "title", "")

        try:
            enrichment = enrich_job_description(
                description,
                title=title,
                use_ai=use_ai,
            )
            _apply_enrichment(job, enrichment)

        except Exception as exc:
            if use_ai and _is_rate_limit_error(exc):
                use_ai = False
                print(
                    "\nGroq daily token limit reached. "
                    "Continuing with deterministic extraction "
                    "so ranking can still run.\n"
                )

            try:
                enrichment = enrich_job_description(
                    description,
                    title=title,
                    use_ai=False,
                )
                _apply_enrichment(job, enrichment)
            except Exception as fallback_exc:
                print(
                    f"[enrichment] failed for "
                    f"{getattr(job, 'company', '')} | "
                    f"{getattr(job, 'title', '')}: "
                    f"{type(fallback_exc).__name__}: {fallback_exc}"
                )

        if (
            index % 5 == 0
            or index == len(jobs_with_descriptions)
        ):
            mode = "Groq" if use_ai else "deterministic"
            print(
                f"  {mode} enrichment: "
                f"{index}/{len(jobs_with_descriptions)}"
            )

        enriched_jobs.append(job)

    jobs_without_descriptions = [
        job
        for job in jobs
        if not (
            getattr(job, "description", "")
            and getattr(job, "description", "").strip()
        )
    ]

    enriched_jobs.extend(jobs_without_descriptions)

    return enriched_jobs

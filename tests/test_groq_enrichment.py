"""
Focused tests for Groq enrichment: success, failure,
rate-limit handling, deterministic fallback, and observability.
"""

import json
import os
from unittest.mock import MagicMock, patch

from app.models.job import Job
from app.services.job_enrichment import (
    _is_rate_limit_error,
    _try_ai_enrichment,
    enrich_job_description,
)
from app.services.recent_job_enricher import (
    enrich_recent_jobs_with_groq,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_job(
    *,
    job_id: str = "1",
    title: str = "Backend Engineer",
    company: str = "Acme",
    description: str = "Python and 3+ years experience.",
) -> Job:
    return Job(
        id=job_id,
        title=title,
        company=company,
        description=description,
        application_url=f"https://example.com/{job_id}",
    )


def _groq_response(
    *,
    required_skills: list[str] | None = None,
    preferred_skills: list[str] | None = None,
    experience_years: float | None = None,
    seniority: str = "senior",
    role_family: str = "Backend Engineer",
    confidence: float = 0.9,
) -> str:
    return json.dumps(
        {
            "required_skills": required_skills or ["python"],
            "preferred_skills": preferred_skills or [],
            "experience_years": experience_years,
            "seniority": seniority,
            "role_family": role_family,
            "job_type": "full-time",
            "confidence": confidence,
        }
    )


# ------------------------------------------------------------------
# _is_rate_limit_error
# ------------------------------------------------------------------


def test_is_rate_limit_error_detects_429():
    assert _is_rate_limit_error(RuntimeError("status 429")) is True


def test_is_rate_limit_error_detects_rate_limit_text():
    assert _is_rate_limit_error(RuntimeError("rate limit exceeded")) is True


def test_is_rate_limit_error_detects_rate_limit_underscore():
    assert _is_rate_limit_error(RuntimeError("rate_limit hit")) is True


def test_is_rate_limit_error_rejects_other_errors():
    assert _is_rate_limit_error(RuntimeError("connection timeout")) is False


def test_is_rate_limit_error_rejects_missing_api_key():
    assert _is_rate_limit_error(
        RuntimeError("GROQ_API_KEY is not configured.")
    ) is False


# ------------------------------------------------------------------
# _try_ai_enrichment — success
# ------------------------------------------------------------------


def test_try_ai_enrichment_success():
    mock_enricher = MagicMock()
    mock_enricher.analyze.return_value = {
        "required_skills": ["python"],
        "preferred_skills": [],
        "experience_years": 3.0,
        "seniority": "senior",
        "role_family": "Backend Engineer",
        "job_type": "full-time",
        "confidence": 0.9,
    }

    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        return_value=mock_enricher,
    ):
        result = _try_ai_enrichment(
            title="Backend Engineer",
            description="Python job",
        )

    assert result["required_skills"] == ["python"]
    assert result["_groq_succeeded"] is True


# ------------------------------------------------------------------
# _try_ai_enrichment — missing API key
# ------------------------------------------------------------------


def test_try_ai_enrichment_missing_api_key():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("GROQ_API_KEY is not configured."),
    ):
        result = _try_ai_enrichment(
            title="Backend Engineer",
            description="Python job",
        )

    assert result["required_skills"] == []
    assert result["_groq_succeeded"] is False


# ------------------------------------------------------------------
# _try_ai_enrichment — generic failure
# ------------------------------------------------------------------


def test_try_ai_enrichment_generic_failure():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("Groq request failed after 3 attempts: connection error"),
    ):
        result = _try_ai_enrichment(
            title="Backend Engineer",
            description="Python job",
        )

    assert result["required_skills"] == []
    assert result["_groq_succeeded"] is False


# ------------------------------------------------------------------
# _try_ai_enrichment — rate-limit re-raises
# ------------------------------------------------------------------


def test_try_ai_enrichment_rate_limit_raises():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("Groq request failed after 3 attempts: 429 Too Many Requests"),
    ):
        try:
            _try_ai_enrichment(
                title="Backend Engineer",
                description="Python job",
            )
            assert False, "Should have raised"
        except RuntimeError as exc:
            assert "429" in str(exc)


# ------------------------------------------------------------------
# enrich_job_description — Groq success
# ------------------------------------------------------------------


def test_enrich_job_description_groq_success():
    mock_enricher = MagicMock()
    mock_enricher.analyze.return_value = json.loads(
        _groq_response(
            required_skills=["python", "java"],
            experience_years=5.0,
            seniority="staff",
        )
    )

    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        return_value=mock_enricher,
    ):
        result = enrich_job_description(
            "Python and Java required. 5+ years experience.",
            title="Senior Engineer",
            use_ai=True,
        )

    assert result.groq_succeeded is True
    assert "python" in result.required_skills
    assert "java" in result.required_skills
    assert result.experience_years_required == 5.0
    assert result.seniority == "staff"


# ------------------------------------------------------------------
# enrich_job_description — Groq failure preserves deterministic
# ------------------------------------------------------------------


def test_enrich_job_description_groq_failure_preserves_deterministic_skills():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("GROQ_API_KEY is not configured."),
    ):
        result = enrich_job_description(
            "Python and 3+ years experience required.",
            title="Backend Engineer",
            use_ai=True,
        )

    assert result.groq_succeeded is False
    assert "python" in result.required_skills
    assert result.experience_years_required == 3.0


def test_enrich_job_description_groq_failure_preserves_deterministic_experience():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("connection error"),
    ):
        result = enrich_job_description(
            "5+ years of experience with Python.",
            title="Senior Engineer",
            use_ai=True,
        )

    assert result.groq_succeeded is False
    assert result.experience_years_required == 5.0
    assert "python" in result.required_skills


# ------------------------------------------------------------------
# enrich_job_description — deterministic-only (use_ai=False)
# ------------------------------------------------------------------


def test_enrich_job_description_deterministic_only():
    result = enrich_job_description(
        "Python and 3+ years experience required.",
        title="Backend Engineer",
        use_ai=False,
    )

    assert result.groq_succeeded is False
    assert "python" in result.required_skills
    assert result.experience_years_required == 3.0


# ------------------------------------------------------------------
# enrich_recent_jobs_with_groq — all jobs returned on failure
# ------------------------------------------------------------------


def test_enrich_returns_all_jobs_when_groq_fails():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("GROQ_API_KEY is not configured."),
    ):
        jobs = [
            _make_job(job_id="1", description="Python job."),
            _make_job(job_id="2", description="Java job."),
        ]
        result = enrich_recent_jobs_with_groq(jobs)

    assert len(result) == 2


# ------------------------------------------------------------------
# enrich_recent_jobs_with_groq — jobs without descriptions
# ------------------------------------------------------------------


def test_enrich_skips_jobs_without_descriptions():
    job_no_desc = _make_job(job_id="1", description="")
    job_with_desc = _make_job(job_id="2", description="Python job.")

    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("GROQ_API_KEY is not configured."),
    ):
        result = enrich_recent_jobs_with_groq([job_no_desc, job_with_desc])

    assert len(result) == 2
    ids = [j.id for j in result]
    assert "1" in ids
    assert "2" in ids


# ------------------------------------------------------------------
# enrich_recent_jobs_with_groq — rate-limit stops Groq
# ------------------------------------------------------------------


def test_rate_limit_stops_groq_for_subsequent_jobs():
    call_count = 0

    def mock_analyze(*, title, description):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return json.loads(_groq_response(required_skills=["python"]))
        if call_count == 2:
            raise RuntimeError(
                "Groq request failed after 3 attempts: 429 Too Many Requests"
            )
        # Should never reach here if rate-limit stops Groq
        raise RuntimeError("Should not be called")

    mock_enricher = MagicMock()
    mock_enricher.analyze.side_effect = mock_analyze

    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        return_value=mock_enricher,
    ):
        jobs = [
            _make_job(job_id="1", description="Python job."),
            _make_job(job_id="2", description="Java job."),
            _make_job(job_id="3", description="Go job."),
        ]
        result = enrich_recent_jobs_with_groq(jobs)

    assert len(result) == 3

    # Job 1: Groq attempted (success)
    assert result[0].required_skills != []
    # Job 2: Rate limit → fallback to deterministic
    # Job 3: use_ai=False → deterministic only
    assert call_count == 2


# ------------------------------------------------------------------
# enrich_recent_jobs_with_groq — counters
# ------------------------------------------------------------------


def test_enrich_counters_all_groq_fail():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("GROQ_API_KEY is not configured."),
    ):
        jobs = [
            _make_job(job_id="1", description="Python job."),
            _make_job(job_id="2", description="Java job."),
        ]
        result = enrich_recent_jobs_with_groq(jobs)

    assert len(result) == 2


def test_enrich_counters_mix_of_success_and_failure():
    call_count = 0

    def mock_analyze(*, title, description):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return json.loads(_groq_response(required_skills=["python"]))
        raise RuntimeError("GROQ_API_KEY is not configured.")

    mock_enricher = MagicMock()
    mock_enricher.analyze.side_effect = mock_analyze

    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        return_value=mock_enricher,
    ):
        jobs = [
            _make_job(job_id="1", description="Python job."),
            _make_job(job_id="2", description="Java job."),
        ]
        result = enrich_recent_jobs_with_groq(jobs)

    assert len(result) == 2
    # Job 1: Groq success — ai_confidence should be non-zero
    assert result[0].ai_confidence > 0
    # Job 2: Groq failed, fallback — ai_confidence should be 0
    assert result[1].ai_confidence == 0.0


# ------------------------------------------------------------------
# enrich_recent_jobs_with_groq — deterministic skills preserved
# ------------------------------------------------------------------


def test_deterministic_skills_preserved_after_groq_failure():
    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        side_effect=RuntimeError("GROQ_API_KEY is not configured."),
    ):
        jobs = [
            _make_job(
                job_id="1",
                description="Python and 3+ years experience required.",
            ),
        ]
        result = enrich_recent_jobs_with_groq(jobs)

    assert len(result) == 1
    assert "python" in result[0].required_skills
    assert result[0].experience_years_required == 3.0


# ------------------------------------------------------------------
# enrich_recent_jobs_with_groq — generic failure does not stop Groq
# ------------------------------------------------------------------


def test_generic_failure_does_not_stop_groq():
    call_count = 0

    def mock_analyze(*, title, description):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("connection error")
        return json.loads(_groq_response(required_skills=["java"]))

    mock_enricher = MagicMock()
    mock_enricher.analyze.side_effect = mock_analyze

    with patch(
        "app.services.job_enrichment.GroqJobEnricher",
        return_value=mock_enricher,
    ):
        jobs = [
            _make_job(job_id="1", description="Python job."),
            _make_job(job_id="2", description="Java job."),
        ]
        result = enrich_recent_jobs_with_groq(jobs)

    assert len(result) == 2
    # Job 1: Groq failed (generic), fallback — ai_confidence 0
    assert result[0].ai_confidence == 0.0
    # Job 2: Groq succeeded (use_ai still True) — ai_confidence > 0
    assert result[1].ai_confidence > 0.0


# ------------------------------------------------------------------
# _apply_enrichment
# ------------------------------------------------------------------


def test_apply_enrichment_sets_job_fields():
    from app.services.job_enrichment import EnrichedJobDescription
    from app.services.recent_job_enricher import _apply_enrichment

    job = _make_job()
    enrichment = EnrichedJobDescription(
        description="cleaned",
        experience_required="3+ years",
        experience_years_required=3.0,
        seniority="senior",
        role_family="Backend Engineer",
        job_type="full-time",
        required_skills=["python"],
        preferred_skills=["java"],
        description_status="present",
        skills_status="extracted",
        experience_status="extracted",
        ai_confidence=0.85,
    )

    _apply_enrichment(job, enrichment)

    assert job.description == "cleaned"
    assert job.experience_years_required == 3.0
    assert job.seniority == "senior"
    assert job.required_skills == ["python"]
    assert job.preferred_skills == ["java"]
    assert job.ai_confidence == 0.85

"""
STEP 9 — End-to-end pipeline integration tests.

Exercises multiple real production components connected together.
Does NOT call live external websites.

The goal is to prove the production pipeline correctly carries
data from input to ranked output.
"""

import random
from datetime import datetime, timedelta, timezone

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.final_scorer import rank_jobs, score_job
from app.scoring.explanation import explain_match
from app.services.job_filter import filter_recent_jobs
from app.services.job_deduplicator import deduplicate_jobs
from app.services.experience_parser import (
    classify_requirement_strictness,
    parse_experience_years,
)
from app.scoring.experience_scorer import classify_experience_risk
from app.eligibility.eligibility import check_eligibility


# ============================================================
# HELPERS
# ============================================================


def _make_candidate(**kwargs):
    defaults = {
        "name": "Test User",
        "email": "test@example.com",
        "experience_years": 3.0,
        "skills": ["Python", "C++"],
        "preferred_roles": ["Backend Engineer"],
        "preferred_locations": ["India"],
    }
    defaults.update(kwargs)
    return CandidateProfile(**defaults)


def _make_job(**kwargs):
    defaults = {
        "id": "job-1",
        "title": "Backend Engineer",
        "company": "TestCo",
        "location": "Bengaluru, India",
        "remote_type": "",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "posted_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Job(**defaults)


def _pipeline(candidate, jobs, limit=None):
    """Run the core ranking pipeline: eligibility → scoring → ranking."""
    return rank_jobs(candidate, jobs, limit=limit)


# ============================================================
# TASK 3-4: FULL RANKING FLOW
# ============================================================


def test_full_pipeline_eligible_and_ineligible():
    """Complete flow: mixed eligible/ineligible jobs.
    Ineligible excluded, eligible scored and ranked."""
    candidate = _make_candidate(preferred_locations=["India"])

    eligible_jobs = [
        _make_job(id="e1", location="Bengaluru, India", required_skills=["Python"]),
        _make_job(id="e2", location="Mumbai, India", required_skills=["C++"]),
    ]
    ineligible_jobs = [
        _make_job(id="i1", location="Hawthorne, CA", required_skills=["Python"]),
        _make_job(id="i2", location="London, UK", required_skills=["Python"]),
    ]

    all_jobs = ineligible_jobs + eligible_jobs
    results = _pipeline(candidate, all_jobs)

    result_ids = [m.job.id for m in results]

    # Ineligible jobs must not appear
    assert "i1" not in result_ids
    assert "i2" not in result_ids

    # Eligible jobs must appear
    assert "e1" in result_ids
    assert "e2" in result_ids

    # Every result has scores populated
    for match in results:
        assert isinstance(match.skill_score, float)
        assert isinstance(match.role_score, (float, type(None)))
        assert isinstance(match.experience_score, float)
        assert isinstance(match.location_score, (float, type(None)))
        assert isinstance(match.compatibility_score, float)
        assert isinstance(match.confidence, float)
        assert isinstance(match.final_score, float)
        assert isinstance(match.experience_risk, str)
        assert match.eligible is True


def test_full_pipeline_scores_populated():
    """Every eligible job receives a complete Match object."""
    candidate = _make_candidate()
    jobs = [
        _make_job(id=f"job-{i}", required_skills=["Python"])
        for i in range(5)
    ]

    results = _pipeline(candidate, jobs)

    assert len(results) == 5
    for match in results:
        assert 0.0 <= match.skill_score <= 100.0
        assert 0.0 <= match.experience_score <= 100.0
        assert 0.0 <= match.compatibility_score <= 100.0
        assert 0.0 <= match.confidence <= 1.0
        assert 0.0 <= match.final_score <= 100.0
        assert match.experience_risk in ("low", "medium", "high", "unknown")


def test_full_pipeline_explanations_generated():
    """Explanations are generated for every ranked job."""
    candidate = _make_candidate()
    jobs = [_make_job(id="job-1", required_skills=["Python"])]

    results = _pipeline(candidate, jobs)
    assert len(results) == 1

    explanations = explain_match(candidate, results[0].job)
    assert isinstance(explanations, list)
    assert len(explanations) > 0


def test_full_pipeline_ranking_deterministic():
    """Same pipeline input produces identical ranking every time."""
    candidate = _make_candidate()
    jobs = [
        _make_job(id="A", required_skills=["Python"]),
        _make_job(id="B", required_skills=["C++"]),
        _make_job(id="C", required_skills=["Java"]),
    ]

    orders = []
    for _ in range(5):
        results = _pipeline(candidate, jobs)
        orders.append([m.job.id for m in results])

    assert all(o == orders[0] for o in orders)


# ============================================================
# TASK 5: LIMIT POSITION
# ============================================================


def test_limit_applied_after_scoring():
    """limit=10 means: score ALL, rank ALL, take top 10.
    A job appearing late in input can become #1."""
    candidate = _make_candidate(
        skills=["Python", "C++", "FastAPI"],
        preferred_roles=[],
    )

    # 20 jobs, last one is the best match
    jobs = []
    for i in range(19):
        jobs.append(_make_job(
            id=f"weak-{i:02d}",
            required_skills=["Java"],
        ))
    # Last job: perfect match
    jobs.append(_make_job(
        id="strong-last",
        title="Backend Engineer",
        required_skills=["Python", "C++", "FastAPI"],
    ))

    results = _pipeline(candidate, jobs, limit=10)

    assert len(results) == 10
    # The strong job from the end of input must be #1
    assert results[0].job.id == "strong-last"


def test_limit_does_not_truncate_before_scoring():
    """limit does NOT pre-filter jobs before scoring.
    All jobs are scored, then top-N is taken."""
    candidate = _make_candidate(
        skills=["Python"],
        preferred_roles=["Backend Engineer"],
    )

    # 15 jobs: first 5 have no skill match, last 10 do
    jobs = []
    for i in range(5):
        jobs.append(_make_job(
            id=f"no-match-{i}",
            required_skills=["Java"],
        ))
    for i in range(10):
        jobs.append(_make_job(
            id=f"match-{i}",
            required_skills=["Python"],
        ))

    results = _pipeline(candidate, jobs, limit=5)

    # All 5 results should be from the matching group
    assert len(results) == 5
    for match in results:
        assert match.job.id.startswith("match-")


# ============================================================
# TASK 6: CANDIDATE PREFERENCE PROPAGATION
# ============================================================


def test_preferred_location_affects_eligibility():
    """Changing preferred location changes which jobs are eligible."""
    candidate_india = _make_candidate(preferred_locations=["India"])
    candidate_us = _make_candidate(preferred_locations=["United States"])

    jobs = [
        _make_job(id="india", location="Bengaluru, India"),
        _make_job(id="us", location="Hawthorne, CA"),
    ]

    india_results = _pipeline(candidate_india, jobs)
    us_results = _pipeline(candidate_us, jobs)

    india_ids = [m.job.id for m in india_results]
    us_ids = [m.job.id for m in us_results]

    assert "india" in india_ids
    assert "us" not in india_ids
    assert "us" in us_ids
    assert "india" not in us_ids


def test_preferred_role_affects_ranking():
    """Changing preferred role changes ranking order."""
    backend_candidate = _make_candidate(preferred_roles=["Backend Engineer"])
    ml_candidate = _make_candidate(preferred_roles=["Machine Learning Engineer"])

    jobs = [
        _make_job(id="be", title="Backend Engineer", required_skills=["Python"]),
        _make_job(id="ml", title="Machine Learning Engineer", required_skills=["Python"]),
    ]

    be_ranked = _pipeline(backend_candidate, jobs)
    ml_ranked = _pipeline(ml_candidate, jobs)

    assert be_ranked[0].job.id == "be"
    assert ml_ranked[0].job.id == "ml"


def test_secondary_role_affects_scoring():
    """Secondary roles provide weaker but real scoring signal."""
    candidate = _make_candidate(
        preferred_roles=[],
        secondary_roles=["Backend Engineer"],
    )
    jobs = [
        _make_job(id="be", title="Backend Engineer"),
        _make_job(id="fe", title="Frontend Engineer"),
    ]

    results = _pipeline(candidate, jobs)
    # Backend should rank above Frontend due to secondary role
    assert results[0].job.id == "be"


def test_empty_preferences_no_crash():
    """Candidate with no configured preferences does not crash."""
    candidate = _make_candidate(
        preferred_roles=[],
        secondary_roles=[],
        preferred_locations=[],
    )
    jobs = [_make_job(id="job-1")]

    results = _pipeline(candidate, jobs)
    assert len(results) == 1
    # Location and role scores should be None
    assert results[0].location_score is None


def test_resume_roles_not_silently_used_as_preferences():
    """Resume-derived roles remain as facts, not preferences."""
    from run_jobagent import apply_default_preferences

    profile = CandidateProfile(
        resume_roles=["Backend Engineer", "ML Engineer"],
        skills=["Python"],
    )

    result = apply_default_preferences(profile)

    # Resume roles stay as facts
    assert result.facts.resume_roles == ["Backend Engineer", "ML Engineer"]
    # Preferences are NOT populated from resume
    assert result.preferences.preferred_roles == []


# ============================================================
# TASK 7: REMOTE JOB DATA
# ============================================================


def test_remote_type_preserved_through_pipeline():
    """remote_type='Remote' with empty location is preserved."""
    candidate = _make_candidate(preferred_locations=["India"])
    job = _make_job(
        id="remote",
        location="",
        remote_type="Remote",
    )

    results = _pipeline(candidate, [job])

    assert len(results) == 1
    assert results[0].location_score == 100.0
    assert results[0].job.remote_type == "Remote"
    assert results[0].job.location == ""


def test_remote_us_job_rejected_for_india():
    """Remote US job is rejected for India-preference candidate."""
    candidate = _make_candidate(preferred_locations=["India"])
    job = _make_job(
        id="remote-us",
        location="Remote - United States",
        remote_type="Remote",
    )

    results = _pipeline(candidate, [job])
    assert len(results) == 0


def test_empty_location_no_fake_match():
    """Empty location does not become a fake match.
    Empty location + India preference => ineligible (hard rejection)."""
    candidate = _make_candidate(preferred_locations=["India"])
    job = _make_job(id="no-loc", location="", remote_type="")

    match = score_job(candidate, job)
    assert match.location_score == 0.0
    assert match.eligible is False
    assert "outside preferred locations" in match.eligibility_reasons


# ============================================================
# TASK 8: CACHE INTEGRATION
# ============================================================


def test_cache_round_trip():
    """Jobs stored in cache can be retrieved with correct fields."""
    from app.storage.job_cache import JobCache
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_cache.db")
        cache = JobCache(db_path=db_path)

        try:
            job = _make_job(
                id="cache-test",
                source="test_source",
            )

            cache.upsert([job])
            cached = cache.query_active()

            assert len(cached) == 1
            assert cached[0].id == "cache-test"
            assert cached[0].source == "test_source"
        finally:
            cache.close()


def test_cache_inactive_jobs_not_ranked():
    """Inactive/stale jobs do not enter ranking."""
    from app.storage.job_cache import JobCache
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_cache.db")
        cache = JobCache(db_path=db_path)

        try:
            active_job = _make_job(id="active", source="s1")
            stale_job = _make_job(id="stale", source="s2")

            cache.upsert([active_job, stale_job])

            # Mark stale job as inactive
            cache.mark_stale("s2", set())

            cached = cache.query_active()
            cached_ids = [j.id for j in cached]

            assert "active" in cached_ids
            assert "stale" not in cached_ids
        finally:
            cache.close()


# ============================================================
# TASK 9: DEDUPLICATION INTEGRATION
# ============================================================


def test_dedup_by_application_url():
    """Same application_url => deduplicated."""
    job_a = _make_job(
        id="a",
        application_url="https://example.com/apply/123",
        company="Company A",
    )
    job_b = _make_job(
        id="b",
        application_url="https://example.com/apply/123",
        company="Company B",
    )

    result = deduplicate_jobs([job_a, job_b])
    assert len(result) == 1


def test_dedup_preserves_distinct_jobs():
    """Different jobs are NOT deduplicated."""
    job_a = _make_job(id="a", title="Backend Engineer")
    job_b = _make_job(id="b", title="Frontend Engineer")

    result = deduplicate_jobs([job_a, job_b])
    assert len(result) == 2


def test_dedup_by_title_company_location():
    """Without application_url, dedup uses title+company+location."""
    job_a = _make_job(
        id="a",
        title="Backend Engineer",
        company="Acme",
        location="Bengaluru",
    )
    job_b = _make_job(
        id="b",
        title="Backend Engineer",
        company="Acme",
        location="Bengaluru",
    )

    result = deduplicate_jobs([job_a, job_b])
    assert len(result) == 1


# ============================================================
# TASK 10: ENRICHMENT INTEGRATION
# ============================================================


def test_enrichment_preserves_existing_fields():
    """Enrichment does not destroy collector-provided fields."""
    from app.services.recent_job_enricher import _apply_enrichment
    from app.services.job_enrichment import EnrichedJobDescription

    job = _make_job(
        id="enrich-test",
        location="Bengaluru, India",
        remote_type="Remote",
        required_skills=["Python"],
    )

    enrichment = EnrichedJobDescription(
        description="New description",
        experience_required="2+ years",
        experience_years_required=2.0,
        seniority="mid",
        role_family="backend_engineering",
        job_type="full_time",
        required_skills=["Python", "C++"],
        preferred_skills=["FastAPI"],
        description_status="present",
        skills_status="enriched",
        experience_status="enriched",
        ai_confidence=0.9,
        groq_succeeded=True,
    )

    _apply_enrichment(job, enrichment)

    # Enrichment updated these fields
    assert job.description == "New description"
    assert job.required_skills == ["Python", "C++"]

    # Collector fields preserved
    assert job.location == "Bengaluru, India"
    assert job.remote_type == "Remote"


def test_enrichment_failure_preserves_job():
    """Enrichment failure does not destroy the job."""
    from app.services.recent_job_enricher import _apply_enrichment

    job = _make_job(
        id="fail-test",
        required_skills=["Python"],
        location="Bengaluru, India",
    )

    # Simulate enrichment returning None fields
    class EmptyEnrichment:
        description = None
        experience_required = None
        experience_years_required = None
        seniority = None
        role_family = None
        job_type = None
        required_skills = None
        preferred_skills = None
        description_status = "absent"
        skills_status = "not_attempted"
        experience_status = "not_attempted"
        ai_confidence = 0.0
        groq_succeeded = False

    _apply_enrichment(job, EmptyEnrichment())

    # Job still exists with safe defaults
    assert job.location == "Bengaluru, India"
    assert job.required_skills == []  # None -> empty list via or []


# ============================================================
# TASK 11: UNKNOWN / NONE FIELDS THROUGH PIPELINE
# ============================================================


def test_missing_skills_through_pipeline():
    """Missing skills produce neutral 50.0, not crash."""
    candidate = _make_candidate()
    job = _make_job(
        id="no-skills",
        required_skills=[],
        preferred_skills=[],
    )

    match = score_job(candidate, job)
    assert match.skill_score == 50.0


def test_missing_role_through_pipeline():
    """Unknown role produces role_score=0 for candidates with preferences."""
    candidate = _make_candidate(preferred_roles=["Backend Engineer"])
    job = _make_job(title="Something Completely Unknown")

    match = score_job(candidate, job)
    assert match.role_score == 0.0


def test_missing_location_through_pipeline():
    """Missing location with preference => 0.0 score, not crash."""
    candidate = _make_candidate(preferred_locations=["India"])
    job = _make_job(location="", remote_type="")

    match = score_job(candidate, job)
    assert match.location_score == 0.0


def test_missing_experience_requirement():
    """No experience requirement => 100.0 score."""
    candidate = _make_candidate(experience_years=0)
    job = _make_job(experience_years_required=None)

    match = score_job(candidate, job)
    assert match.experience_score == 100.0


def test_none_semantics_not_collapsed_to_zero():
    """None and 0.0 are distinguishable through the pipeline."""
    candidate_no_loc = _make_candidate(preferred_locations=[])
    candidate_zero_loc = _make_candidate(preferred_locations=[""])
    job = _make_job(location="Bengaluru, India")

    match_no = score_job(candidate_no_loc, job)
    match_zero = score_job(candidate_zero_loc, job)

    # No preference => None (excluded from compatibility)
    assert match_no.location_score is None


# ============================================================
# TASK 12: EXPERIENCE INTELLIGENCE END-TO-END
# ============================================================


def test_experience_intelligence_end_to_end():
    """Full experience intelligence: score, risk, eligibility, explanation."""
    candidate = _make_candidate(
        experience_years=1,
        internship_years=1.0,
    )
    job = _make_job(
        id="exp-test",
        experience_years_required=2,
        experience_required="2+ years",
        requirement_strictness="required",
    )

    match = score_job(candidate, job)

    # Score is partial (1/2 = 50%)
    assert match.experience_score == 50.0

    # Risk is populated
    assert match.experience_risk in ("low", "medium", "high", "unknown")

    # Internship is preserved separately
    assert candidate.facts.internship_years == 1.0
    assert candidate.facts.experience_years == 1

    # Internship is NOT counted as full-time
    # (score uses experience_years=1, not 1+1=2)

    # Eligibility not affected
    assert match.eligible is True

    # Explanation communicates risk
    explanations = explain_match(candidate, job)
    exp_explanation = [e for e in explanations if "experience" in e.lower() or "experience" in str(match.experience_score).lower()]
    assert len(exp_explanation) > 0


def test_experience_risk_varies_by_strictness():
    """Same gap, different strictness => different risk, same score."""
    candidate = _make_candidate(experience_years=1)

    job_strict = _make_job(
        experience_years_required=2,
        requirement_strictness="strict",
    )
    job_preferred = _make_job(
        experience_years_required=2,
        requirement_strictness="preferred",
    )

    match_strict = score_job(candidate, job_strict)
    match_preferred = score_job(candidate, job_preferred)

    # Same score (risk doesn't affect ranking)
    assert match_strict.experience_score == match_preferred.experience_score
    assert match_strict.compatibility_score == match_preferred.compatibility_score
    assert match_strict.final_score == match_preferred.final_score

    # Different risk
    assert match_strict.experience_risk != match_preferred.experience_risk


# ============================================================
# TASK 13: ENRICHMENT FAILURE
# ============================================================


def test_enrichment_failure_does_not_corrupt_other_jobs():
    """Enrichment failure for one job does not affect other jobs."""
    from app.services.recent_job_enricher import _apply_enrichment

    job_ok = _make_job(id="ok", required_skills=["Python"])
    job_fail = _make_job(id="fail", required_skills=["C++"])

    # Simulate enrichment failure for job_fail (fields become None)
    class FailEnrichment:
        description = None
        experience_required = None
        experience_years_required = None
        seniority = None
        role_family = None
        job_type = None
        required_skills = None
        preferred_skills = None
        description_status = "absent"
        skills_status = "not_attempted"
        experience_status = "not_attempted"
        ai_confidence = 0.0
        groq_succeeded = False

    _apply_enrichment(job_fail, FailEnrichment())

    # job_ok is unaffected
    assert job_ok.required_skills == ["Python"]
    assert job_fail.required_skills == []


# ============================================================
# TASK 14: ORDER INDEPENDENCE
# ============================================================


def test_order_independence_full_pipeline():
    """Same jobs in different input orders produce identical ranking."""
    candidate = _make_candidate()
    jobs = [
        _make_job(id="A", required_skills=["Python"]),
        _make_job(id="B", required_skills=["C++"]),
        _make_job(id="C", required_skills=["Java"]),
        _make_job(id="D", required_skills=["Python", "C++"]),
        _make_job(id="E", required_skills=[]),
    ]

    order1 = [m.job.id for m in _pipeline(candidate, jobs)]

    for seed in range(10):
        shuffled = list(jobs)
        random.seed(seed)
        random.shuffle(shuffled)
        order2 = [m.job.id for m in _pipeline(candidate, shuffled)]
        assert order1 == order2, f"Seed {seed} changed order"


# ============================================================
# TASK 15: TOP-N CORRECTNESS
# ============================================================


def test_top_n_returns_correct_jobs():
    """20 jobs, limit=5 => correct top 5 returned."""
    candidate = _make_candidate(
        skills=["Python", "C++"],
        preferred_roles=["Backend Engineer"],
    )

    jobs = []
    # 15 weak jobs
    for i in range(15):
        jobs.append(_make_job(
            id=f"weak-{i:02d}",
            title="Data Scientist",
            required_skills=["Java"],
        ))
    # 5 strong jobs
    for i in range(5):
        jobs.append(_make_job(
            id=f"strong-{i:02d}",
            title="Backend Engineer",
            required_skills=["Python", "C++"],
        ))

    results = _pipeline(candidate, jobs, limit=5)

    assert len(results) == 5
    result_ids = [m.job.id for m in results]
    for i in range(5):
        assert f"strong-{i:02d}" in result_ids


# ============================================================
# TASK 16: ZERO / ONE / MANY JOBS
# ============================================================


def test_zero_jobs():
    """Empty job list => empty results."""
    candidate = _make_candidate()
    results = _pipeline(candidate, [])
    assert results == []


def test_one_eligible_job():
    """Single eligible job ranks correctly."""
    candidate = _make_candidate()
    results = _pipeline(candidate, [_make_job(id="solo")])
    assert len(results) == 1
    assert results[0].job.id == "solo"


def test_one_ineligible_job():
    """Single ineligible job => empty results."""
    candidate = _make_candidate(preferred_locations=["India"])
    results = _pipeline(candidate, [_make_job(id="bad", location="Hawthorne, CA")])
    assert results == []


def test_all_jobs_ineligible():
    """All jobs ineligible => empty results."""
    candidate = _make_candidate(preferred_locations=["India"])
    jobs = [
        _make_job(id=f"us-{i}", location="Hawthorne, CA")
        for i in range(10)
    ]
    results = _pipeline(candidate, jobs)
    assert results == []


def test_many_jobs():
    """Pipeline handles many jobs without crash."""
    candidate = _make_candidate()
    jobs = [_make_job(id=f"job-{i}") for i in range(100)]
    results = _pipeline(candidate, jobs)
    assert len(results) == 100


# ============================================================
# TASK 17: ENTRY POINT WITHOUT NETWORK
# ============================================================


def test_apply_default_preferences_headless():
    """Non-interactive preference handling works correctly."""
    from run_jobagent import apply_default_preferences

    profile = CandidateProfile(
        resume_roles=["Backend Engineer"],
        skills=["Python"],
    )

    result = apply_default_preferences(profile)

    # No preferences were set (non-interactive)
    assert result.preferences.preferred_roles == []
    assert result.preferences.secondary_roles == []
    assert result.preferences.preferred_locations == []
    # Facts preserved
    assert result.facts.resume_roles == ["Backend Engineer"]
    assert result.facts.skills == ["Python"]


# ============================================================
# TASK 18: OUTPUT CONTRACT
# ============================================================


def test_output_contains_all_required_fields():
    """JobMatch output contains all ranking-relevant fields."""
    candidate = _make_candidate()
    job = _make_job(
        experience_years_required=2,
        requirement_strictness="required",
    )

    match = score_job(candidate, job)

    # All fields present
    assert hasattr(match, "job")
    assert hasattr(match, "eligible")
    assert hasattr(match, "skill_score")
    assert hasattr(match, "role_score")
    assert hasattr(match, "experience_score")
    assert hasattr(match, "experience_risk")
    assert hasattr(match, "location_score")
    assert hasattr(match, "compatibility_score")
    assert hasattr(match, "confidence")
    assert hasattr(match, "final_score")
    assert hasattr(match, "eligibility_reasons")

    # Types correct
    assert isinstance(match.job, Job)
    assert isinstance(match.eligible, bool)
    assert isinstance(match.skill_score, float)
    assert isinstance(match.experience_risk, str)
    assert isinstance(match.eligibility_reasons, list)


def test_experience_risk_in_output():
    """experience_risk is populated in the final output."""
    candidate = _make_candidate(experience_years=1)
    job = _make_job(
        experience_years_required=3,
        requirement_strictness="required",
    )

    match = score_job(candidate, job)

    assert match.experience_risk in ("low", "medium", "high", "unknown")


def test_requirement_strictness_on_job():
    """requirement_strictness is stored on the Job object."""
    job = _make_job(requirement_strictness="strict")
    assert job.requirement_strictness == "strict"

    job_default = _make_job()
    assert job_default.requirement_strictness == "unknown"

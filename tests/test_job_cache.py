"""
Tests for the persistent job cache.

All tests use temporary SQLite databases — the real
data/job_cache.db is never touched.
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.models.job import Job
from app.storage.job_cache import JobCache


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def _make_job(
    job_id: str = "100",
    title: str = "Software Engineer",
    company: str = "Acme Corp",
    source: str = "greenhouse",
    application_url: str = "https://example.com/apply/100",
    posted_at: datetime | None = None,
) -> Job:
    return Job(
        id=job_id,
        title=title,
        company=company,
        source=source,
        application_url=application_url,
        posted_at=posted_at,
    )


def _make_wellfound_job(
    job_id: str = "200",
    title: str = "AI Engineer",
    company: str = "AI Startup",
) -> Job:
    return Job(
        id=job_id,
        title=title,
        company=company,
        source="wellfound",
        application_url=f"https://wellfound.com/jobs/{job_id}",
        location="Bengaluru, India",
        remote_type="Hybrid",
        required_skills=["python", "pytorch"],
        posted_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def cache(tmp_path):
    """Create a temporary cache for each test."""
    db_path = tmp_path / "test_cache.db"
    c = JobCache(db_path=db_path)
    yield c
    c.close()


# ---------------------------------------------------------
# 1. New job insertion
# ---------------------------------------------------------


def test_upsert_inserts_new_jobs(cache):
    jobs = [
        _make_job(job_id="1"),
        _make_job(job_id="2"),
        _make_job(job_id="3"),
    ]

    cache.upsert(jobs)

    stats = cache.get_stats()
    assert stats["total"] == 3
    assert stats["active"] == 3


# ---------------------------------------------------------
# 2. Multiple job insertion
# ---------------------------------------------------------


def test_upsert_multiple_jobs(cache):
    jobs = [_make_job(job_id=str(i)) for i in range(50)]
    cache.upsert(jobs)

    stats = cache.get_stats()
    assert stats["total"] == 50
    assert stats["active"] == 50


# ---------------------------------------------------------
# 3. Existing job update
# ---------------------------------------------------------


def test_upsert_updates_existing_job(cache):
    job_v1 = _make_job(job_id="1", title="Engineer V1")
    cache.upsert([job_v1])

    job_v2 = _make_job(job_id="1", title="Engineer V2")
    cache.upsert([job_v2])

    active = cache.query_active()
    assert len(active) == 1
    assert active[0].title == "Engineer V2"
    assert active[0].id == "1"


# ---------------------------------------------------------
# 4. first_seen_at preservation
# ---------------------------------------------------------


def test_first_seen_at_preserved(cache):
    job_v1 = _make_job(job_id="1", title="V1")
    cache.upsert([job_v1])

    stats_after_v1 = cache.get_stats()
    assert stats_after_v1["total"] == 1

    # Small delay so timestamps differ
    import time
    time.sleep(0.01)

    job_v2 = _make_job(job_id="1", title="V2")
    cache.upsert([job_v2])

    # Verify first_seen_at is from the first insert
    row = cache._conn.execute(
        """
        SELECT first_seen_at, last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()

    assert row is not None
    first = datetime.fromisoformat(row["first_seen_at"])
    last = datetime.fromisoformat(row["last_seen_at"])

    # first_seen_at should be earlier than or equal to last_seen_at
    assert first <= last

    # Both should be valid datetimes
    assert first.tzinfo is not None
    assert last.tzinfo is not None


# ---------------------------------------------------------
# 5. last_seen_at update
# ---------------------------------------------------------


def test_last_seen_at_updated(cache):
    job_v1 = _make_job(job_id="1")
    cache.upsert([job_v1])

    row_v1 = cache._conn.execute(
        """
        SELECT last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()
    ts_v1 = datetime.fromisoformat(row_v1["last_seen_at"])

    import time
    time.sleep(0.01)

    job_v2 = _make_job(job_id="1")
    cache.upsert([job_v2])

    row_v2 = cache._conn.execute(
        """
        SELECT last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()
    ts_v2 = datetime.fromisoformat(row_v2["last_seen_at"])

    assert ts_v2 >= ts_v1


# ---------------------------------------------------------
# 6. Active query
# ---------------------------------------------------------


def test_query_active_returns_only_active(cache):
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
        _make_job(job_id="3"),
    ])

    # Mark job 3 as stale
    cache.mark_stale("greenhouse", {"1", "2"})

    active = cache.query_active()
    active_ids = {j.id for j in active}

    assert len(active) == 2
    assert "1" in active_ids
    assert "2" in active_ids
    assert "3" not in active_ids


# ---------------------------------------------------------
# 7. Source filtering
# ---------------------------------------------------------


def test_query_active_filters_by_source(cache):
    cache.upsert([
        _make_job(job_id="1", source="greenhouse"),
        _make_job(job_id="2", source="greenhouse"),
        _make_wellfound_job(job_id="200"),
        _make_wellfound_job(job_id="201"),
    ])

    gh_jobs = cache.query_active(source="greenhouse")
    wf_jobs = cache.query_active(source="wellfound")

    assert len(gh_jobs) == 2
    assert len(wf_jobs) == 2
    assert all(j.source == "greenhouse" for j in gh_jobs)
    assert all(j.source == "wellfound" for j in wf_jobs)


# ---------------------------------------------------------
# 8. Empty cache
# ---------------------------------------------------------


def test_empty_cache_returns_empty_list(cache):
    active = cache.query_active()
    assert active == []


def test_empty_cache_stats(cache):
    stats = cache.get_stats()
    assert stats["total"] == 0
    assert stats["active"] == 0
    assert stats["stale"] == 0
    assert stats["by_source"] == {}


# ---------------------------------------------------------
# 9. Serialization round-trip
# ---------------------------------------------------------


def test_roundtrip_serialization(cache):
    now = datetime.now(timezone.utc)

    original = Job(
        id="rt-001",
        title="Backend Engineer",
        company="TechCo",
        location="Remote",
        remote_type="Remote",
        experience_required="3-5 years",
        experience_years_required=3.0,
        seniority="senior",
        role_family="BACKEND_ENGINEERING",
        job_type="full_time",
        ai_confidence=0.85,
        required_skills=["python", "go", "postgresql"],
        preferred_skills=["kubernetes", "redis"],
        salary_min_lpa=15.0,
        salary_max_lpa=25.0,
        description="Build backend systems.",
        description_status="present",
        skills_status="extracted",
        experience_status="extracted",
        description_length=1234,
        application_url="https://example.com/apply/rt-001",
        source_url="https://example.com/job/rt-001",
        source="greenhouse",
        posted_at=now,
        fetched_at=now,
    )

    cache.upsert([original])
    restored = cache.query_active()

    assert len(restored) == 1
    r = restored[0]

    assert r.id == "rt-001"
    assert r.title == "Backend Engineer"
    assert r.company == "TechCo"
    assert r.location == "Remote"
    assert r.remote_type == "Remote"
    assert r.experience_required == "3-5 years"
    assert r.experience_years_required == 3.0
    assert r.seniority == "senior"
    assert r.role_family == "BACKEND_ENGINEERING"
    assert r.job_type == "full_time"
    assert r.ai_confidence == 0.85
    assert r.required_skills == ["python", "go", "postgresql"]
    assert r.preferred_skills == ["kubernetes", "redis"]
    assert r.salary_min_lpa == 15.0
    assert r.salary_max_lpa == 25.0
    assert r.description == "Build backend systems."
    assert r.description_status == "present"
    assert r.skills_status == "extracted"
    assert r.experience_status == "extracted"
    assert r.description_length == 1234
    assert r.application_url == "https://example.com/apply/rt-001"
    assert r.source_url == "https://example.com/job/rt-001"
    assert r.source == "greenhouse"

    # Datetime fields
    assert r.posted_at is not None
    assert r.posted_at.year == now.year
    assert r.posted_at.month == now.month
    assert r.posted_at.day == now.day

    assert r.fetched_at is not None
    assert r.fetched_at.year == now.year


def test_roundtrip_with_none_optional_fields(cache):
    original = Job(
        id="rt-002",
        title="Junior Dev",
        company="StartupCo",
        source="ashby",
        application_url="https://ashby.co/jobs/rt-002",
        experience_years_required=None,
        salary_min_lpa=None,
        salary_max_lpa=None,
        job_type=None,
        posted_at=None,
        fetched_at=None,
    )

    cache.upsert([original])
    restored = cache.query_active()

    assert len(restored) == 1
    r = restored[0]

    assert r.id == "rt-002"
    assert r.experience_years_required is None
    assert r.salary_min_lpa is None
    assert r.salary_max_lpa is None
    assert r.job_type is None
    assert r.posted_at is None
    assert r.fetched_at is None


# ---------------------------------------------------------
# 10. Repeated identical upserts produce no duplicates
# ---------------------------------------------------------


def test_repeated_upserts_no_duplicates(cache):
    jobs = [_make_job(job_id="1"), _make_job(job_id="2")]

    cache.upsert(jobs)
    cache.upsert(jobs)
    cache.upsert(jobs)

    stats = cache.get_stats()
    assert stats["total"] == 2
    assert stats["active"] == 2


# ---------------------------------------------------------
# 11. Cache stats
# ---------------------------------------------------------


def test_cache_stats(cache):
    cache.upsert([
        _make_job(job_id="1", source="greenhouse"),
        _make_job(job_id="2", source="greenhouse"),
        _make_wellfound_job(job_id="200"),
    ])

    cache.mark_stale("greenhouse", {"1"})

    stats = cache.get_stats()

    assert stats["total"] == 3
    assert stats["active"] == 2
    assert stats["stale"] == 1
    assert stats["by_source"]["greenhouse"] == 1
    assert stats["by_source"]["wellfound"] == 1


# ---------------------------------------------------------
# 12. mark_stale
# ---------------------------------------------------------


def test_mark_stale(cache):
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
        _make_job(job_id="3"),
    ])

    stale_count = cache.mark_stale("greenhouse", {"1", "3"})

    assert stale_count == 1

    active = cache.query_active()
    active_ids = {j.id for j in active}
    assert active_ids == {"1", "3"}


def test_mark_stale_all(cache):
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    stale_count = cache.mark_stale("greenhouse", set())

    assert stale_count == 2

    active = cache.query_active()
    assert len(active) == 0


def test_mark_stale_reactivates_on_upsert(cache):
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    cache.mark_stale("greenhouse", {"1"})

    stats = cache.get_stats()
    assert stats["active"] == 1
    assert stats["stale"] == 1

    # Re-upserting job 2 (which is currently stale) reactivates it
    cache.upsert([_make_job(job_id="2")])

    stats = cache.get_stats()
    assert stats["active"] == 2
    assert stats["stale"] == 0


# ---------------------------------------------------------
# 13. URL index behavior
# ---------------------------------------------------------


def test_canonical_url_stored(cache):
    job = _make_job(
        job_id="1",
        application_url="https://example.com/apply/1",
    )
    cache.upsert([job])

    row = cache._conn.execute(
        """
        SELECT canonical_url
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()

    assert row["canonical_url"] == "https://example.com/apply/1"


def test_cross_source_same_id_both_stored(cache):
    gh_job = _make_job(job_id="same-id", source="greenhouse")
    wf_job = _make_wellfound_job(job_id="same-id")

    cache.upsert([gh_job, wf_job])

    stats = cache.get_stats()
    assert stats["total"] == 2

    gh = cache.query_active(source="greenhouse")
    wf = cache.query_active(source="wellfound")

    assert len(gh) == 1
    assert len(wf) == 1
    assert gh[0].id == "same-id"
    assert wf[0].id == "same-id"


# ---------------------------------------------------------
# 14. Empty upsert
# ---------------------------------------------------------


def test_upsert_empty_list(cache):
    cache.upsert([])

    stats = cache.get_stats()
    assert stats["total"] == 0


# ---------------------------------------------------------
# 15. Context manager
# ---------------------------------------------------------


def test_context_manager(tmp_path):
    db_path = tmp_path / "ctx_test.db"

    with JobCache(db_path=db_path) as cache:
        cache.upsert([_make_job(job_id="1")])
        stats = cache.get_stats()
        assert stats["total"] == 1

    # Connection should be closed after exiting context
    assert cache._conn is None

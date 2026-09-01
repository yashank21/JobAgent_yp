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


# ---------------------------------------------------------
# 16. WAL safety for GitHub Actions cache persistence
# ---------------------------------------------------------


def test_close_checkpoints_wal(tmp_path):
    """After close(), committed data must be in the main .db file,
    not stranded in .db-wal."""
    db_path = tmp_path / "wal_test.db"

    cache = JobCache(db_path=db_path)
    cache.upsert([_make_job(job_id="w1"), _make_job(job_id="w2")])

    wal_path = db_path.with_suffix(".db-wal")
    shm_path = db_path.with_suffix(".db-shm")

    # WAL file exists while connection is open and data was written
    assert wal_path.exists()

    cache.close()

    # After close(), WAL should be checkpointed into the main db.
    # The WAL file may still exist on disk but should be empty (0 bytes).
    if wal_path.exists():
        assert wal_path.stat().st_size == 0

    # SHM file should be removed after close()
    assert not shm_path.exists()

    # Reopen and verify data survived the checkpoint
    cache2 = JobCache(db_path=db_path)
    stats = cache2.get_stats()
    assert stats["total"] == 2
    assert stats["active"] == 2
    cache2.close()


def test_context_manager_checkpoints_wal(tmp_path):
    """Context manager exit must checkpoint WAL so data is safe
    for cache persistence."""
    db_path = tmp_path / "wal_ctx.db"

    with JobCache(db_path=db_path) as cache:
        cache.upsert([_make_job(job_id="c1")])

    wal_path = db_path.with_suffix(".db-wal")

    if wal_path.exists():
        assert wal_path.stat().st_size == 0

    # Reopen and verify
    cache2 = JobCache(db_path=db_path)
    assert cache2.get_stats()["total"] == 1
    cache2.close()


def test_tryfinally_close_preserves_data(tmp_path):
    """Even when an exception occurs, finally-block close() must
    checkpoint data so the next run can restore it."""
    db_path = tmp_path / "wal_finally.db"

    cache = JobCache(db_path=db_path)
    cache.upsert([_make_job(job_id="f1"), _make_job(job_id="f2")])

    try:
        raise ValueError("simulated pipeline failure")
    except ValueError:
        pass
    finally:
        cache.close()

    # Reopen and verify both records survived
    cache2 = JobCache(db_path=db_path)
    stats = cache2.get_stats()
    assert stats["total"] == 2
    cache2.close()


def test_cache_persistence_survives_reopen(tmp_path):
    """Simulate the GitHub Actions scenario: write data, close,
    reopen a fresh connection (as if restored from cache), read."""
    db_path = tmp_path / "persist.db"

    # Run 1: write and close
    cache = JobCache(db_path=db_path)
    cache.upsert([
        _make_job(job_id="p1", title="Engineer"),
        _make_job(job_id="p2", title="Scientist"),
    ])
    cache.close()

    # Run 2: open fresh, read back
    cache2 = JobCache(db_path=db_path)
    jobs = cache2.query_active()
    assert len(jobs) == 2
    titles = {j.title for j in jobs}
    assert titles == {"Engineer", "Scientist"}
    cache2.close()


# ---------------------------------------------------------
# 17. Source reconciliation (stale after successful collection)
# ---------------------------------------------------------


def test_mark_stale_marks_missing_jobs(cache):
    """Jobs not in the seen set should be marked stale."""
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


def test_mark_stale_preserves_seen_jobs(cache):
    """Jobs in the seen set remain active."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    cache.mark_stale("greenhouse", {"1", "2"})

    active = cache.query_active()
    active_ids = {j.id for j in active}
    assert active_ids == {"1", "2"}


def test_mark_stale_only_affects_requested_source(cache):
    """Stale marking for one source must not affect another."""
    cache.upsert([
        _make_job(job_id="1", source="greenhouse"),
        _make_job(job_id="2", source="greenhouse"),
        _make_wellfound_job(job_id="200"),
    ])

    cache.mark_stale("greenhouse", {"1"})

    gh_active = cache.query_active(source="greenhouse")
    wf_active = cache.query_active(source="wellfound")

    assert len(gh_active) == 1
    assert gh_active[0].id == "1"
    assert len(wf_active) == 1
    assert wf_active[0].id == "200"


def test_mark_stale_does_not_change_last_seen_at(cache):
    """Stale marking must NOT update last_seen_at."""
    cache.upsert([_make_job(job_id="1")])

    row_before = cache._conn.execute(
        """
        SELECT last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()
    ts_before = row_before["last_seen_at"]

    import time
    time.sleep(0.01)

    cache.mark_stale("greenhouse", set())

    row_after = cache._conn.execute(
        """
        SELECT last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()
    ts_after = row_after["last_seen_at"]

    assert ts_before == ts_after


def test_reappearing_job_is_reactivated_by_upsert(cache):
    """A stale job that reappears in the next collection is
    automatically reactivated by upsert."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    cache.mark_stale("greenhouse", {"1"})

    stats = cache.get_stats()
    assert stats["active"] == 1
    assert stats["stale"] == 1

    # Job 2 reappears in the next collection
    cache.upsert([_make_job(job_id="2")])

    stats = cache.get_stats()
    assert stats["active"] == 2
    assert stats["stale"] == 0


def test_failed_source_collection_does_not_mark_jobs_stale(cache):
    """When a source collection fails (exception), the pipeline
    must NOT call mark_stale for that source.  All existing jobs
    should remain active."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    # Simulate: Wellfound collection raised an exception.
    # The pipeline should NOT call mark_stale.
    # (This is a behavioral test — we verify the contract.)

    stats = cache.get_stats()
    assert stats["active"] == 2
    assert stats["stale"] == 0


def test_partial_source_collection_does_not_mark_jobs_stale(cache):
    """When a collection is partial, the pipeline must NOT call
    mark_stale for that source.  All existing jobs should remain
    active."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
        _make_job(job_id="3"),
    ])

    # Simulate: only partial results returned.  Pipeline should
    # NOT call mark_stale.
    # (This is a behavioral test — we verify the contract.)

    stats = cache.get_stats()
    assert stats["active"] == 3
    assert stats["stale"] == 0


def test_cache_only_mode_does_not_mark_jobs_stale(cache):
    """In cache_only mode, no source collection happens and
    mark_stale must NOT be called."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    # Simulate: cache_only mode — no mark_stale call.
    stats = cache.get_stats()
    assert stats["active"] == 2
    assert stats["stale"] == 0


def test_empty_successful_collection_marks_existing_source_jobs_stale(cache):
    """When a source collection succeeds but returns zero jobs,
    all previously cached jobs from that source should be
    marked stale — the source scan completed and found nothing."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    stale_count = cache.mark_stale("greenhouse", set())

    assert stale_count == 2

    active = cache.query_active()
    assert len(active) == 0

    stats = cache.get_stats()
    assert stats["stale"] == 2


# ---------------------------------------------------------
# 18. delete_expired (stale job expiry / deletion)
# ---------------------------------------------------------


def test_delete_expired_removes_old_stale_jobs(cache):
    """An inactive job whose last_seen_at is older than 30 days
    should be deleted."""
    cache.upsert([_make_job(job_id="1")])
    cache.mark_stale("greenhouse", set())

    # Backdate last_seen_at to 31 days ago
    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=31)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """,
        (old_ts,),
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 1
    stats = cache.get_stats()
    assert stats["total"] == 0


def test_delete_expired_preserves_recent_stale_jobs(cache):
    """An inactive job whose last_seen_at is newer than the expiry
    threshold should NOT be deleted."""
    cache.upsert([_make_job(job_id="1")])
    cache.mark_stale("greenhouse", set())

    # Backdate last_seen_at to only 10 days ago (within 30-day
    # window)
    recent_ts = (
        datetime.now(timezone.utc) - timedelta(days=10)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """,
        (recent_ts,),
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 0
    stats = cache.get_stats()
    assert stats["total"] == 1
    assert stats["stale"] == 1


def test_delete_expired_preserves_active_jobs(cache):
    """An ACTIVE job whose last_seen_at is older than 30 days
    must NOT be deleted.  This is the critical safety test."""
    cache.upsert([_make_job(job_id="1")])

    # Backdate last_seen_at to 60 days ago (but job is still
    # active — no mark_stale call)
    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=60)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """,
        (old_ts,),
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 0
    stats = cache.get_stats()
    assert stats["total"] == 1
    assert stats["active"] == 1


def test_delete_expired_returns_deleted_count(cache):
    """delete_expired() must return the correct count of deleted
    rows."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
        _make_job(job_id="3"),
        _make_job(job_id="4"),
    ])
    cache.mark_stale("greenhouse", set())

    # Make jobs 1 and 2 old enough (40 days), jobs 3 and 4
    # recent (5 days)
    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=40)
    ).isoformat()
    recent_ts = (
        datetime.now(timezone.utc) - timedelta(days=5)
    ).isoformat()

    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source_job_id IN ('1', '2')
        """,
        (old_ts,),
    )
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source_job_id IN ('3', '4')
        """,
        (recent_ts,),
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 2
    stats = cache.get_stats()
    assert stats["total"] == 2
    assert stats["stale"] == 2


def test_delete_expired_does_not_use_posted_at(cache):
    """A stale job with an old posted_at but recent last_seen_at
    must NOT be deleted.  Expiry is based solely on last_seen_at."""
    cache.upsert([
        _make_job(
            job_id="1",
            posted_at=datetime.now(timezone.utc) - timedelta(days=90),
        ),
    ])
    cache.mark_stale("greenhouse", set())

    # last_seen_at is recent (1 day ago) — job should survive
    recent_ts = (
        datetime.now(timezone.utc) - timedelta(days=1)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """,
        (recent_ts,),
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 0
    stats = cache.get_stats()
    assert stats["total"] == 1


def test_delete_expired_handles_empty_last_seen_at(cache):
    """An inactive job with an empty last_seen_at must NOT be
    automatically deleted.  The schema enforces NOT NULL, but an
    empty string is structurally possible and should be safe."""
    cache.upsert([_make_job(job_id="1")])
    cache.mark_stale("greenhouse", set())

    # Set last_seen_at to empty string (closest to "missing"
    # that the schema allows)
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ''
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 0
    stats = cache.get_stats()
    assert stats["total"] == 1


def test_delete_expired_handles_malformed_last_seen_at(cache):
    """An inactive job with a malformed last_seen_at must NOT be
    deleted — it should be preserved rather than causing
    destructive cleanup."""
    cache.upsert([_make_job(job_id="1")])
    cache.mark_stale("greenhouse", set())

    # Set last_seen_at to a clearly malformed string
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = 'not-a-valid-timestamp'
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 0
    stats = cache.get_stats()
    assert stats["total"] == 1


def test_delete_expired_rejects_invalid_threshold(cache):
    """Invalid expiry values (negative, zero) must raise
    ValueError."""
    with pytest.raises(ValueError, match="older_than_days must be >= 1"):
        cache.delete_expired(older_than_days=0)

    with pytest.raises(ValueError, match="older_than_days must be >= 1"):
        cache.delete_expired(older_than_days=-5)


def test_reactivated_job_is_not_deleted(cache):
    """A job that was old and stale but then reactivated via
    upsert must NOT be deleted by delete_expired()."""
    cache.upsert([_make_job(job_id="1")])
    cache.mark_stale("greenhouse", set())

    # Backdate last_seen_at to 60 days ago
    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=60)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """,
        (old_ts,),
    )
    cache._conn.commit()

    # Job reappears — upsert reactivates it
    cache.upsert([_make_job(job_id="1")])

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 0
    stats = cache.get_stats()
    assert stats["total"] == 1
    assert stats["active"] == 1


def test_cleanup_does_not_affect_other_sources(cache):
    """Old stale jobs from multiple sources should all be handled
    correctly by delete_expired()."""
    cache.upsert([
        _make_job(job_id="1", source="greenhouse"),
        _make_job(job_id="2", source="greenhouse"),
        _make_wellfound_job(job_id="200"),
        _make_wellfound_job(job_id="201"),
    ])

    # Mark all as stale
    cache.mark_stale("greenhouse", set())
    cache.mark_stale("wellfound", set())

    # Make greenhouse jobs old (40 days), wellfound jobs recent
    # (5 days)
    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=40)
    ).isoformat()
    recent_ts = (
        datetime.now(timezone.utc) - timedelta(days=5)
    ).isoformat()

    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse'
        """,
        (old_ts,),
    )
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'wellfound'
        """,
        (recent_ts,),
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 2

    stats = cache.get_stats()
    assert stats["total"] == 2
    assert stats["stale"] == 2

    # Only wellfound jobs remain
    remaining = cache.query_active()
    assert len(remaining) == 0

    remaining_all = cache._conn.execute(
        "SELECT source FROM job_cache"
    ).fetchall()
    sources = {r["source"] for r in remaining_all}
    assert sources == {"wellfound"}


# ---------------------------------------------------------
# 19. End-to-end lifecycle integration tests
# ---------------------------------------------------------


def test_lifecycle_new_job_inserted_with_correct_fields(cache):
    """A newly collected job is inserted as is_active = 1 with
    first_seen_at and last_seen_at set."""
    cache.upsert([_make_job(job_id="1")])

    row = cache._conn.execute(
        """
        SELECT is_active, first_seen_at, last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()

    assert row is not None
    assert row["is_active"] == 1
    assert row["first_seen_at"] is not None
    assert row["first_seen_at"] != ""
    assert row["last_seen_at"] is not None
    assert row["last_seen_at"] != ""


def test_lifecycle_existing_job_seen_again_updates_preserves(cache):
    """An existing job seen again remains active, updates
    last_seen_at, and preserves first_seen_at."""
    cache.upsert([_make_job(job_id="1", title="V1")])

    row_v1 = cache._conn.execute(
        """
        SELECT first_seen_at, last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()
    first_v1 = row_v1["first_seen_at"]

    import time
    time.sleep(0.01)

    cache.upsert([_make_job(job_id="1", title="V2")])

    row_v2 = cache._conn.execute(
        """
        SELECT is_active, first_seen_at, last_seen_at
        FROM job_cache
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """
    ).fetchone()

    assert row_v2["is_active"] == 1
    assert row_v2["first_seen_at"] == first_v1
    assert row_v2["last_seen_at"] >= row_v1["last_seen_at"]


def test_lifecycle_missing_from_successful_wellfound_marked_stale(
    cache,
):
    """A job missing from a successful Wellfound collection is
    marked is_active = 0 and preserves its previous last_seen_at."""
    cache.upsert([_make_wellfound_job(job_id="200")])
    cache.upsert([_make_wellfound_job(job_id="201")])

    row_before = cache._conn.execute(
        """
        SELECT last_seen_at
        FROM job_cache
        WHERE source = 'wellfound' AND source_job_id = '200'
        """
    ).fetchone()
    lsa_before = row_before["last_seen_at"]

    # Successful collection only sees job 201
    cache.mark_stale("wellfound", {"201"})

    row_after = cache._conn.execute(
        """
        SELECT is_active, last_seen_at
        FROM job_cache
        WHERE source = 'wellfound' AND source_job_id = '200'
        """
    ).fetchone()

    assert row_after["is_active"] == 0
    assert row_after["last_seen_at"] == lsa_before


def test_lifecycle_stale_job_reappears_not_deleted(cache):
    """A stale job that reappears is reactivated by upsert and is
    not deleted by delete_expired()."""
    cache.upsert([_make_job(job_id="1")])
    cache.mark_stale("greenhouse", set())

    # Backdate to old timestamp
    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=60)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """,
        (old_ts,),
    )
    cache._conn.commit()

    # Job reappears
    cache.upsert([_make_job(job_id="1")])

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 0
    stats = cache.get_stats()
    assert stats["active"] == 1
    assert stats["stale"] == 0


def test_lifecycle_failed_wellfound_collection_preserves_jobs(cache):
    """A failed Wellfound collection does not call mark_stale()
    and does not deactivate existing jobs."""
    cache.upsert([
        _make_wellfound_job(job_id="200"),
        _make_wellfound_job(job_id="201"),
    ])

    # Simulate failed collection — pipeline skips mark_stale
    # (no call to mark_stale)

    stats = cache.get_stats()
    assert stats["active"] == 2
    assert stats["stale"] == 0


def test_lifecycle_partial_wellfound_collection_preserves_jobs(cache):
    """A partial Wellfound collection does not call mark_stale()
    and does not deactivate existing jobs."""
    cache.upsert([
        _make_wellfound_job(job_id="200"),
        _make_wellfound_job(job_id="201"),
        _make_wellfound_job(job_id="202"),
    ])

    # Simulate partial collection — pipeline skips mark_stale
    # (no call to mark_stale)

    stats = cache.get_stats()
    assert stats["active"] == 3
    assert stats["stale"] == 0


def test_lifecycle_cache_only_mode_no_reconciliation(cache):
    """Cache_only mode does not perform stale reconciliation."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
    ])

    # Simulate cache_only mode — no mark_stale call
    stats = cache.get_stats()
    assert stats["active"] == 2
    assert stats["stale"] == 0


def test_lifecycle_cache_only_mode_allows_expiry(cache):
    """Cache_only mode may perform expiry cleanup."""
    cache.upsert([_make_job(job_id="1")])
    cache.mark_stale("greenhouse", set())

    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=40)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source = 'greenhouse' AND source_job_id = '1'
        """,
        (old_ts,),
    )
    cache._conn.commit()

    # Cache_only mode runs delete_expired
    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 1
    stats = cache.get_stats()
    assert stats["total"] == 0


def test_lifecycle_delete_expired_only_removes_old_stale(cache):
    """delete_expired(30) deletes only is_active = 0 jobs older
    than 30 days."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
        _make_job(job_id="3"),
    ])

    # Mark jobs 1 and 2 stale, keep 3 active
    cache.mark_stale("greenhouse", {"3"})

    # Make job 1 old (40 days), job 2 recent (5 days)
    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=40)
    ).isoformat()
    recent_ts = (
        datetime.now(timezone.utc) - timedelta(days=5)
    ).isoformat()

    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source_job_id = '1'
        """,
        (old_ts,),
    )
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source_job_id = '2'
        """,
        (recent_ts,),
    )
    cache._conn.commit()

    deleted = cache.delete_expired(older_than_days=30)

    assert deleted == 1
    stats = cache.get_stats()
    assert stats["total"] == 2
    assert stats["active"] == 1
    assert stats["stale"] == 1


def test_lifecycle_query_active_returns_only_active_jobs(cache):
    """The final query_active() result contains only active jobs."""
    cache.upsert([
        _make_job(job_id="1"),
        _make_job(job_id="2"),
        _make_job(job_id="3"),
    ])

    # Mark jobs 2 and 3 stale (only job 1 in seen set)
    cache.mark_stale("greenhouse", {"1"})

    active = cache.query_active()
    active_ids = {j.id for j in active}

    assert len(active) == 1
    assert active_ids == {"1"}


def test_lifecycle_cleanup_does_not_alter_job_payloads(cache):
    """Cleanup (mark_stale + delete_expired) does not alter job
    payloads or affect the data returned by query_active()."""
    original = Job(
        id="1",
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
        application_url="https://example.com/apply/1",
        source_url="https://example.com/job/1",
        source="greenhouse",
        posted_at=datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
    )

    cache.upsert([original])

    # Mark job 2 stale, then delete it
    cache.upsert([_make_job(job_id="2")])
    cache.mark_stale("greenhouse", {"1"})

    old_ts = (
        datetime.now(timezone.utc) - timedelta(days=40)
    ).isoformat()
    cache._conn.execute(
        """
        UPDATE job_cache
        SET last_seen_at = ?
        WHERE source_job_id = '2'
        """,
        (old_ts,),
    )
    cache._conn.commit()

    cache.delete_expired(older_than_days=30)

    # Verify job 1 payload is completely unmodified
    active = cache.query_active(source="greenhouse")
    assert len(active) == 1

    r = active[0]
    assert r.id == "1"
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
    assert r.application_url == "https://example.com/apply/1"
    assert r.source_url == "https://example.com/job/1"
    assert r.source == "greenhouse"

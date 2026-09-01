"""
Persistent job cache backed by SQLite.

Source-agnostic: works with Wellfound, Greenhouse, Lever,
Ashby, Workday, and any future source.

Primary key: (source, source_job_id)

The cache stores normalized Job objects as JSON blobs
with metadata columns for indexing and querying.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.models.job import Job


DEFAULT_CACHE_PATH = Path("data/job_cache.db")


class JobCache:
    """Source-agnostic persistent job cache backed by SQLite."""

    def __init__(
        self,
        db_path: Path | str = DEFAULT_CACHE_PATH,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")

        self._create_table()

    # ---------------------------------------------------------
    # Schema
    # ---------------------------------------------------------

    def _create_table(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS job_cache (
                source          TEXT    NOT NULL,
                source_job_id   TEXT    NOT NULL,
                canonical_url   TEXT    NOT NULL DEFAULT '',
                job_json        TEXT    NOT NULL,
                first_seen_at   TEXT    NOT NULL,
                last_seen_at    TEXT    NOT NULL,
                last_updated_at TEXT,
                is_active       INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (source, source_job_id)
            );

            CREATE INDEX IF NOT EXISTS idx_job_cache_canonical_url
                ON job_cache(canonical_url);

            CREATE INDEX IF NOT EXISTS idx_job_cache_is_active
                ON job_cache(is_active);

            CREATE INDEX IF NOT EXISTS idx_job_cache_source_active
                ON job_cache(source, is_active);
            """
        )
        self._conn.commit()

    # ---------------------------------------------------------
    # Serialization
    # ---------------------------------------------------------

    @staticmethod
    def _serialize_job(job: Job) -> str:
        """Serialize a Job to a JSON string."""
        data = asdict(job)

        if job.posted_at is not None:
            data["posted_at"] = job.posted_at.isoformat()

        if job.fetched_at is not None:
            data["fetched_at"] = job.fetched_at.isoformat()

        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    def _deserialize_job(raw_json: str) -> Job:
        """Deserialize a JSON string back to a Job object."""
        data = json.loads(raw_json)

        posted_at = data.get("posted_at")
        if posted_at and isinstance(posted_at, str):
            data["posted_at"] = datetime.fromisoformat(posted_at)
        elif posted_at is None:
            data["posted_at"] = None

        fetched_at = data.get("fetched_at")
        if fetched_at and isinstance(fetched_at, str):
            data["fetched_at"] = datetime.fromisoformat(fetched_at)
        elif fetched_at is None:
            data["fetched_at"] = None

        # Filter to known Job fields so extra JSON keys
        # do not break construction.
        known_fields = {
            f.name for f in Job.__dataclass_fields__.values()
        }

        filtered = {k: v for k, v in data.items() if k in known_fields}

        return Job(**filtered)

    # ---------------------------------------------------------
    # Upsert
    # ---------------------------------------------------------

    def upsert(self, jobs: list[Job]) -> None:
        """
        Insert or update jobs in the cache.

        On first insert:
            first_seen_at = now
            last_seen_at = now
            is_active = 1

        On existing job (same source + source_job_id):
            first_seen_at = preserved (NOT overwritten)
            last_seen_at = now
            job payload = updated
            is_active = 1 (reactivated if previously stale)
        """
        if not jobs:
            return

        now = datetime.now(timezone.utc).isoformat()

        inserted = 0
        updated = 0

        for job in jobs:
            source = job.source or ""
            source_job_id = job.id or ""
            canonical_url = job.application_url or ""

            existing = self._conn.execute(
                """
                SELECT first_seen_at
                FROM job_cache
                WHERE source = ? AND source_job_id = ?
                """,
                (source, source_job_id),
            ).fetchone()

            job_json = self._serialize_job(job)

            if existing is None:
                self._conn.execute(
                    """
                    INSERT INTO job_cache
                        (source, source_job_id, canonical_url,
                         job_json, first_seen_at, last_seen_at,
                         last_updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (source, source_job_id, canonical_url,
                     job_json, now, now, now),
                )
                inserted += 1
            else:
                first_seen_at = existing["first_seen_at"]

                self._conn.execute(
                    """
                    UPDATE job_cache
                    SET canonical_url = ?,
                        job_json = ?,
                        last_seen_at = ?,
                        last_updated_at = ?,
                        is_active = 1
                    WHERE source = ? AND source_job_id = ?
                    """,
                    (canonical_url, job_json, now, now,
                     source, source_job_id),
                )
                updated += 1

        self._conn.commit()

        print(
            f"Cache upsert: {inserted} inserted, "
            f"{updated} updated, "
            f"{len(jobs)} total"
        )

    # ---------------------------------------------------------
    # Query
    # ---------------------------------------------------------

    def query_active(
        self,
        source: str | None = None,
    ) -> list[Job]:
        """
        Return all active cached jobs as Job objects.

        Optionally filter by source.
        """
        if source is not None:
            rows = self._conn.execute(
                """
                SELECT job_json
                FROM job_cache
                WHERE is_active = 1 AND source = ?
                ORDER BY last_seen_at DESC
                """,
                (source,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT job_json
                FROM job_cache
                WHERE is_active = 1
                ORDER BY last_seen_at DESC
                """,
            ).fetchall()

        return [self._deserialize_job(row["job_json"]) for row in rows]

    # ---------------------------------------------------------
    # Stale (available but NOT auto-called by pipeline)
    # ---------------------------------------------------------

    def mark_stale(
        self,
        source: str,
        active_ids: set[str],
    ) -> int:
        """
        Mark jobs from a source as stale when their ID
        is not in active_ids.

        This is available for manual or policy-driven use.
        The normal production pipeline does NOT call this
        automatically.
        """
        placeholder = ",".join("?" for _ in active_ids) if active_ids else "''"

        if active_ids:
            cursor = self._conn.execute(
                f"""
                UPDATE job_cache
                SET is_active = 0
                WHERE source = ?
                  AND is_active = 1
                  AND source_job_id NOT IN ({placeholder})
                """,
                [source, *active_ids],
            )
        else:
            cursor = self._conn.execute(
                """
                UPDATE job_cache
                SET is_active = 0
                WHERE source = ? AND is_active = 1
                """,
                (source,),
            )

        self._conn.commit()

        count = cursor.rowcount

        if count > 0:
            print(
                f"Cache mark_stale: {count} jobs marked stale "
                f"for source '{source}'"
            )

        return count

    # ---------------------------------------------------------
    # Stats
    # ---------------------------------------------------------

    def get_stats(self) -> dict:
        """Return cache statistics."""
        row = self._conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) AS active,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) AS stale
            FROM job_cache
            """
        ).fetchone()

        sources = self._conn.execute(
            """
            SELECT source, COUNT(*) AS cnt
            FROM job_cache
            WHERE is_active = 1
            GROUP BY source
            ORDER BY cnt DESC
            """
        ).fetchall()

        return {
            "total": row["total"],
            "active": row["active"] or 0,
            "stale": row["stale"] or 0,
            "by_source": {r["source"]: r["cnt"] for r in sources},
        }

    # ---------------------------------------------------------
    # Cleanup
    # ---------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

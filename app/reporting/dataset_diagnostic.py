"""
Dataset-level diagnostic report for JobAgent.

Analyzes the complete normalized job dataset without changing
eligibility, scoring, or ranking behavior.

This module is intentionally measurement-only.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from statistics import mean, median
from typing import Any

from app.eligibility.eligibility import check_eligibility
from app.filters.freshness import is_recent_job
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.experience_scorer import calculate_experience_score
from app.scoring.job_scorer import calculate_skill_score
from app.scoring.role_scorer import calculate_role_score
from app.scoring.final_scorer import (
    calculate_final_score,
    calculate_location_score,
)
from app.scoring.role_normalizer import classify_role
from app.eligibility.seniority import classify_seniority


# ============================================================
# REPORT MODEL
# ============================================================

@dataclass
class DatasetDiagnostic:
    collection: dict[str, Any] = field(default_factory=dict)
    data_quality: dict[str, Any] = field(default_factory=dict)
    location: dict[str, Any] = field(default_factory=dict)
    experience: dict[str, Any] = field(default_factory=dict)
    seniority: dict[str, Any] = field(default_factory=dict)
    roles: dict[str, Any] = field(default_factory=dict)
    skills: dict[str, Any] = field(default_factory=dict)
    eligibility: dict[str, Any] = field(default_factory=dict)
    scoring: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# HELPERS
# ============================================================

def _distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
        }

    return {
        "count": len(values),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
    }


def _score_buckets(scores: list[float]) -> dict[str, int]:
    buckets = {
        "0-20": 0,
        "20-40": 0,
        "40-60": 0,
        "60-70": 0,
        "70-80": 0,
        "80-90": 0,
        "90-100": 0,
    }

    for score in scores:
        if score < 20:
            buckets["0-20"] += 1
        elif score < 40:
            buckets["20-40"] += 1
        elif score < 60:
            buckets["40-60"] += 1
        elif score < 70:
            buckets["60-70"] += 1
        elif score < 80:
            buckets["70-80"] += 1
        elif score < 90:
            buckets["80-90"] += 1
        else:
            buckets["90-100"] += 1

    return buckets


def _top_counter(
    counter: Counter[str],
    limit: int = 20,
) -> list[dict[str, Any]]:
    return [
        {
            "value": value,
            "count": count,
        }
        for value, count in counter.most_common(limit)
    ]


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_dataset(
    candidate: CandidateProfile,
    jobs: list[Job],
) -> DatasetDiagnostic:

    total = len(jobs)

    # --------------------------------------------------------
    # Collection
    # --------------------------------------------------------

    ids = [job.id for job in jobs]
    urls = [
        job.application_url
        for job in jobs
        if job.application_url
    ]

    id_counts = Counter(ids)
    url_counts = Counter(urls)

    duplicate_ids = sum(
        count - 1
        for count in id_counts.values()
        if count > 1
    )

    duplicate_urls = sum(
        count - 1
        for count in url_counts.values()
        if count > 1
    )

    source_counts = Counter(
        job.source or "unknown"
        for job in jobs
    )

    report = DatasetDiagnostic()

    report.collection = {
        "total_jobs": total,
        "unique_ids": len(set(ids)),
        "duplicate_ids": duplicate_ids,
        "unique_urls": len(set(urls)),
        "duplicate_urls": duplicate_urls,
        "by_source": dict(source_counts),
    }

    # --------------------------------------------------------
    # Data quality
    # --------------------------------------------------------

    report.data_quality = {
        "missing_title": sum(
            not job.title for job in jobs
        ),
        "missing_company": sum(
            not job.company for job in jobs
        ),
        "missing_description": sum(
            not job.description for job in jobs
        ),
        "missing_location": sum(
            not job.location for job in jobs
        ),
        "missing_remote_type": sum(
            not job.remote_type for job in jobs
        ),
        "missing_experience": sum(
            job.experience_years_required is None
            for job in jobs
        ),
        "missing_required_skills": sum(
            not job.required_skills
            for job in jobs
        ),
        "missing_preferred_skills": sum(
            not job.preferred_skills
            for job in jobs
        ),
        "missing_salary": sum(
            job.salary_min_lpa is None
            and job.salary_max_lpa is None
            for job in jobs
        ),
        "missing_application_url": sum(
            not job.application_url
            for job in jobs
        ),
    }

    # --------------------------------------------------------
    # Location
    # --------------------------------------------------------

    location_categories = Counter()

    for job in jobs:
        location = (
            job.location or ""
        ).strip().lower()

        remote_type = (
            job.remote_type or ""
        ).strip().lower()

        if "remote" in remote_type or "remote" in location:
            if "india" in location or "india" in remote_type:
                location_categories["remote_india"] += 1
            elif any(
                country in location
                for country in [
                    "united states",
                    "united kingdom",
                    "canada",
                    "australia",
                    "germany",
                    "france",
                    "poland",
                    "singapore",
                    "ireland",
                    "japan",
                ]
            ):
                location_categories["remote_foreign"] += 1
            else:
                location_categories["remote_unknown"] += 1

        elif not location:
            location_categories["unknown"] += 1

        elif "india" in location:
            location_categories["india"] += 1

        else:
            location_categories["other"] += 1

    report.location = {
        "categories": dict(location_categories),
        "missing_location_and_remote": sum(
            not job.location
            and "remote" in (
                job.remote_type or ""
            ).lower()
            for job in jobs
        ),
    }

    # --------------------------------------------------------
    # Experience
    # --------------------------------------------------------

    experience_values = [
        job.experience_years_required
        for job in jobs
        if job.experience_years_required is not None
    ]

    experience_buckets = {
        "missing": 0,
        "0": 0,
        "0-1": 0,
        "1-2": 0,
        "2-3": 0,
        "3-5": 0,
        "5-8": 0,
        "8+": 0,
    }

    for job in jobs:
        years = job.experience_years_required

        if years is None:
            experience_buckets["missing"] += 1
        elif years <= 0:
            experience_buckets["0"] += 1
        elif years < 1:
            experience_buckets["0-1"] += 1
        elif years < 2:
            experience_buckets["1-2"] += 1
        elif years < 3:
            experience_buckets["2-3"] += 1
        elif years < 5:
            experience_buckets["3-5"] += 1
        elif years < 8:
            experience_buckets["5-8"] += 1
        else:
            experience_buckets["8+"] += 1

    report.experience = {
        "candidate_years": candidate.experience_years,
        "distribution": _distribution(
            [float(value) for value in experience_values]
        ),
        "buckets": experience_buckets,
    }

    # --------------------------------------------------------
    # Seniority
    # --------------------------------------------------------

    seniority_counts = Counter(
        classify_seniority(job.title)
        for job in jobs
    )

    report.seniority = dict(seniority_counts)

    # --------------------------------------------------------
    # Roles
    # --------------------------------------------------------

    role_counts = Counter(
        str(classify_role(job.title))
        for job in jobs
    )

    report.roles = dict(role_counts)

    # --------------------------------------------------------
    # Skills
    # --------------------------------------------------------

    required_skill_counts = Counter()
    preferred_skill_counts = Counter()

    required_skill_counts_per_job = []
    preferred_skill_counts_per_job = []

    for job in jobs:
        required = job.required_skills or []
        preferred = job.preferred_skills or []

        required_skill_counts.update(
            skill.lower().strip()
            for skill in required
            if skill
        )

        preferred_skill_counts.update(
            skill.lower().strip()
            for skill in preferred
            if skill
        )

        required_skill_counts_per_job.append(
            len(required)
        )

        preferred_skill_counts_per_job.append(
            len(preferred)
        )

    report.skills = {
        "required_skills_per_job": _distribution(
            [
                float(value)
                for value in required_skill_counts_per_job
            ]
        ),
        "preferred_skills_per_job": _distribution(
            [
                float(value)
                for value in preferred_skill_counts_per_job
            ]
        ),
        "jobs_with_zero_required_skills": sum(
            value == 0
            for value in required_skill_counts_per_job
        ),
        "jobs_with_zero_preferred_skills": sum(
            value == 0
            for value in preferred_skill_counts_per_job
        ),
        "top_required_skills": _top_counter(
            required_skill_counts
        ),
        "top_preferred_skills": _top_counter(
            preferred_skill_counts
        ),
    }

    # --------------------------------------------------------
    # Freshness + eligibility + scoring
    # --------------------------------------------------------

    fresh_count = 0
    eligible_count = 0

    rejection_reasons = Counter()

    skill_scores = []
    role_scores = []
    experience_scores = []
    location_scores = []
    final_scores = []

    experience_gap_count = 0
    seniority_warning_count = 0

    for job in jobs:

        fresh = is_recent_job(
            job,
            hours=48,
        )

        if not fresh:
            continue

        fresh_count += 1

        eligibility = check_eligibility(
            candidate,
            job,
        )

        for reason in eligibility.reasons:
            if reason.startswith("experience gap:"):
                experience_gap_count += 1

            elif reason.startswith("seniority:"):
                seniority_warning_count += 1

            else:
                rejection_reasons[reason] += 1

        if not eligibility.eligible:
            continue

        eligible_count += 1

        skill_score = calculate_skill_score(
            candidate,
            job,
        )

        role_score = calculate_role_score(
            candidate,
            job,
        )

        experience_score = calculate_experience_score(
            candidate,
            job,
        )

        location_score = calculate_location_score(
            candidate,
            job,
        )

        final_score = calculate_final_score(
            skill_score=skill_score,
            role_score=role_score,
            experience_score=experience_score,
            location_score=location_score,
        )

        skill_scores.append(skill_score)
        role_scores.append(role_score)
        experience_scores.append(experience_score)
        location_scores.append(location_score)
        final_scores.append(final_score)

    # --------------------------------------------------------
    # Eligibility report
    # --------------------------------------------------------

    report.eligibility = {
        "collected": total,
        "fresh": fresh_count,
        "stale": total - fresh_count,
        "eligible": eligible_count,
        "rejected": fresh_count - eligible_count,
        "rejection_reasons": dict(rejection_reasons),
        "experience_gap_warnings": experience_gap_count,
        "seniority_warnings": seniority_warning_count,
    }

    # --------------------------------------------------------
    # Scoring report
    # --------------------------------------------------------

    report.scoring = {
        "scored_jobs": len(final_scores),

        "skill": _distribution(skill_scores),
        "role": _distribution(role_scores),
        "experience": _distribution(experience_scores),
        "location": _distribution(location_scores),
        "final": _distribution(final_scores),

        "final_score_buckets": _score_buckets(
            final_scores
        ),

        "weights": {
            "skill": 0.40,
            "role": 0.30,
            "experience": 0.20,
            "location": 0.10,
        },
    }

    return report


# ============================================================
# CONSOLE REPORT
# ============================================================

def print_diagnostic_report(
    report: DatasetDiagnostic,
) -> None:

    print()
    print("=" * 70)
    print("JOBAGENT DATASET DIAGNOSTIC REPORT")
    print("=" * 70)

    print()
    print("[COLLECTION]")

    for key, value in report.collection.items():
        print(f"{key}: {value}")

    print()
    print("[DATA QUALITY]")

    for key, value in report.data_quality.items():
        print(f"{key}: {value}")

    print()
    print("[LOCATION]")

    for key, value in report.location.items():
        print(f"{key}: {value}")

    print()
    print("[EXPERIENCE]")

    for key, value in report.experience.items():
        print(f"{key}: {value}")

    print()
    print("[SENIORITY]")

    for key, value in report.seniority.items():
        print(f"{key}: {value}")

    print()
    print("[ROLES]")

    for key, value in report.roles.items():
        print(f"{key}: {value}")

    print()
    print("[SKILLS]")

    for key, value in report.skills.items():
        print(f"{key}: {value}")

    print()
    print("[ELIGIBILITY]")

    for key, value in report.eligibility.items():
        print(f"{key}: {value}")

    print()
    print("[SCORING]")

    for key, value in report.scoring.items():
        print(f"{key}: {value}")

    print()
    print("=" * 70)

"""
Final job ranking utilities.

V3 ranking is designed to prioritize genuine job fit rather than
allowing generic keyword overlap to dominate the ranking.

Ranking considers:

- Required/preferred skill alignment
- Role alignment
- Experience alignment
- Location compatibility

Strong mismatches receive additional penalties so that a job with
very poor skill or experience alignment cannot rank highly merely
because its title or location looks attractive.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.match import JobMatch

from app.eligibility.eligibility import check_eligibility
from app.scoring.job_scorer import calculate_skill_score
from app.scoring.role_scorer import calculate_role_score
from app.scoring.experience_scorer import calculate_experience_score
from app.filters.freshness import is_recent_job


# ============================================================
# V3 WEIGHTS
# ============================================================

ROLE_WEIGHT = 0.30
SKILL_WEIGHT = 0.40
EXPERIENCE_WEIGHT = 0.20
LOCATION_WEIGHT = 0.10


# ============================================================
# LOCATION
# ============================================================

def calculate_location_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate location compatibility from 0 to 100.

    For an India-focused candidate:

    Explicit Indian location
        -> 100

    Explicit India remote
        -> 100

    Explicit foreign location
        -> 0

    Explicit foreign remote
        -> 0

    Generic remote with unknown country
        -> 0

    Unknown/non-matching location
        -> 0

    IMPORTANT:
    Generic remote must NOT automatically receive 100 because
    remote does not mean remote from India.
    """

    if not candidate.preferred_locations:
        return 100.0

    job_location = (
        job.location or ""
    ).lower().strip()

    remote_type = (
        job.remote_type or ""
    ).lower().strip()

    # --------------------------------------------------------
    # Explicit Indian locations
    # --------------------------------------------------------

    india_locations = [
        "india",
        "bengaluru",
        "bangalore",
        "hyderabad",
        "pune",
        "noida",
        "gurugram",
        "gurgaon",
        "mumbai",
        "delhi",
        "new delhi",
        "chennai",
        "kolkata",
        "ahmedabad",
        "indore",
    ]

    if any(
        location in job_location
        for location in india_locations
    ):
        return 100.0

    # --------------------------------------------------------
    # Explicit foreign locations
    # --------------------------------------------------------

    foreign_locations = [
        "united states",
        "united kingdom",
        "canada",
        "australia",
        "germany",
        "france",
        "poland",
        "colombia",
        "brazil",
        "mexico",
        "singapore",
        "ireland",
        "netherlands",
        "spain",
        "italy",
        "switzerland",
        "japan",
        "china",
        "south korea",
        "israel",
        "uae",
        "dubai",
    ]

    if any(
        country in job_location
        for country in foreign_locations
    ):
        return 0.0

    # --------------------------------------------------------
    # Explicit India remote
    # --------------------------------------------------------

    if (
        "remote - india" in job_location
        or "remote, india" in job_location
        or "remote india" in job_location
        or "india remote" in job_location
        or "india" in remote_type
    ):
        return 100.0

    # --------------------------------------------------------
    # Generic remote
    #
    # We do NOT know where the employee can work.
    #
    # Therefore this cannot be treated as a location match.
    # --------------------------------------------------------

    if (
        "remote" in job_location
        or "remote" in remote_type
    ):
        return 0.0

    # --------------------------------------------------------
    # Unknown / unmatched location
    # --------------------------------------------------------

    return 0.0


# ============================================================
# FINAL SCORE
# ============================================================

def calculate_final_score(
    skill_score: float,
    role_score: float,
    experience_score: float,
    location_score: float,
) -> float:
    """
    Calculate final job compatibility score.

    The weighted score is followed by targeted penalties.

    The goal is:

        Strong skills + strong role
            -> high score

        Strong role + weak skills
            -> moderate score

        Strong role + zero skills
            -> low score

        Strong role + severe experience mismatch
            -> heavily reduced score

        Wrong role
            -> very low score
    """

    # --------------------------------------------------------
    # Base weighted score
    # --------------------------------------------------------

    raw_score = (
        skill_score * SKILL_WEIGHT
        + role_score * ROLE_WEIGHT
        + experience_score * EXPERIENCE_WEIGHT
        + location_score * LOCATION_WEIGHT
    )

    # --------------------------------------------------------
    # ROLE PENALTIES
    # --------------------------------------------------------

    if role_score == 0:
        raw_score = min(
            raw_score,
            20.0,
        )

    elif role_score < 40:
        raw_score = min(
            raw_score,
            35.0,
        )

    elif role_score < 60:
        raw_score = min(
            raw_score,
            50.0,
        )

    elif role_score < 75:
        raw_score = min(
            raw_score,
            65.0,
        )

    # --------------------------------------------------------
    # SKILL PENALTIES
    # --------------------------------------------------------
    #
    # This is the major fix.
    #
    # A job with zero skill overlap should NOT be able to
    # reach 45% merely because role/location are good.
    # --------------------------------------------------------

    if skill_score == 0:

        raw_score = min(
            raw_score,
            30.0,
        )

    elif skill_score < 10:

        raw_score = min(
            raw_score,
            35.0,
        )

    elif skill_score < 20:

        raw_score = min(
            raw_score,
            42.0,
        )

    elif skill_score < 40:

        raw_score = min(
            raw_score,
            55.0,
        )

    # --------------------------------------------------------
    # EXPERIENCE PENALTIES
    # --------------------------------------------------------

    if experience_score < 10:

        raw_score = min(
            raw_score,
            35.0,
        )

    elif experience_score < 20:

        raw_score = min(
            raw_score,
            45.0,
        )

    elif experience_score < 40:

        raw_score = min(
            raw_score,
            55.0,
        )

    elif experience_score < 60:

        raw_score = min(
            raw_score,
            68.0,
        )

    # --------------------------------------------------------
    # COMBINED BAD-FIT PENALTIES
    # --------------------------------------------------------
    #
    # These prevent a job from surviving through one strong
    # dimension when two major dimensions are terrible.
    # --------------------------------------------------------

    # Very weak skills + weak experience
    if (
        skill_score < 20
        and experience_score < 40
    ):
        raw_score = min(
            raw_score,
            35.0,
        )

    # Zero skills + weak role
    if (
        skill_score == 0
        and role_score < 60
    ):
        raw_score = min(
            raw_score,
            25.0,
        )

    # Zero skills + severe experience mismatch
    if (
        skill_score == 0
        and experience_score < 20
    ):
        raw_score = min(
            raw_score,
            25.0,
        )

    return round(
        max(
            0.0,
            min(
                100.0,
                raw_score,
            ),
        ),
        2,
    )


# ============================================================
# INDIVIDUAL JOB
# ============================================================

def score_job(
    candidate: CandidateProfile,
    job: Job,
) -> JobMatch:
    """
    Produce a complete JobMatch for one job.
    """

    eligibility = check_eligibility(
        candidate,
        job,
    )

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

    return JobMatch(
        job=job,
        eligible=eligibility.eligible,
        skill_score=round(
            skill_score,
            2,
        ),
        role_score=round(
            role_score,
            2,
        ),
        experience_score=round(
            experience_score,
            2,
        ),
        location_score=round(
            location_score,
            2,
        ),
        final_score=final_score,
        eligibility_reasons=eligibility.reasons,
    )


# ============================================================
# RANKING
# ============================================================

def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
) -> list[JobMatch]:
    """
    Score jobs posted within the last 48 hours
    and return eligible jobs from highest to lowest.
    """

    # --------------------------------------------------------
    # 1. Freshness filter
    # --------------------------------------------------------

    recent_jobs = [
        job
        for job in jobs
        if is_recent_job(
            job,
            hours=48,
        )
    ]

    # --------------------------------------------------------
    # 2. Score recent jobs
    # --------------------------------------------------------

    matches = [
        score_job(
            candidate,
            job,
        )
        for job in recent_jobs
    ]

    # --------------------------------------------------------
    # 3. Keep only eligible jobs
    # --------------------------------------------------------

    eligible_matches = [
        match
        for match in matches
        if match.eligible
    ]

    # --------------------------------------------------------
    # 4. Rank
    # --------------------------------------------------------

    return sorted(
        eligible_matches,
        key=lambda match: match.final_score,
        reverse=True,
    )
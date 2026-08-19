"""
Final job ranking utilities.

V2 ranking is intentionally not a simple weighted average.

A job must first pass hard eligibility checks. Among eligible jobs,
role alignment, required-skill alignment, experience, and location
determine the ranking.

Score caps prevent strong keyword overlap from hiding major
role/seniority mismatches.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.match import JobMatch

from app.eligibility.eligibility import check_eligibility
from app.scoring.job_scorer import calculate_skill_score
from app.scoring.role_scorer import calculate_role_score
from app.scoring.experience_scorer import calculate_experience_score


# ------------------------------------------------------------
# V2 weights
# ------------------------------------------------------------

ROLE_WEIGHT = 0.30
SKILL_WEIGHT = 0.40
EXPERIENCE_WEIGHT = 0.20
LOCATION_WEIGHT = 0.10



# ------------------------------------------------------------
# Location
# ------------------------------------------------------------

def calculate_location_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate location compatibility from 0 to 100.

    For an India-focused candidate:
    - India locations -> 100
    - Explicit India remote -> 100
    - Generic remote -> 0 because country is unknown
    - US/UK/etc. remote -> 0
    """

    if not candidate.preferred_locations:
        return 100.0

    job_location = (job.location or "").lower().strip()
    remote_type = (job.remote_type or "").lower().strip()

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
    # Explicit foreign remote locations
    # --------------------------------------------------------

    foreign_remote_locations = [
        "remote - us",
        "remote - usa",
        "remote - united states",
        "remote, us",
        "remote, usa",
        "remote, united states",
        "remote - uk",
        "remote, uk",
        "remote - united kingdom",
        "remote, united kingdom",
        "remote - canada",
        "remote, canada",
        "remote - australia",
        "remote, australia",
        "remote - germany",
        "remote, germany",
        "remote - france",
        "remote, france",
        "remote - poland",
        "remote, poland",
    ]

    if any(
        foreign in job_location
        for foreign in foreign_remote_locations
    ):
        return 0.0

    # --------------------------------------------------------
    # Explicit India remote
    # --------------------------------------------------------

    if (
        "remote - india" in job_location
        or "remote india" in job_location
        or "india remote" in job_location
        or "india" in remote_type
    ):
        return 100.0

    # --------------------------------------------------------
    # Generic remote
    #
    # Country is unknown, so keep it eligible for now.
    # --------------------------------------------------------

    if (
        "remote" in job_location
        or "remote" in remote_type
    ):
        return 100.0
    
    return 0.0
# ------------------------------------------------------------
# Final score
# ------------------------------------------------------------

def calculate_final_score(
    skill_score: float,
    role_score: float,
    experience_score: float,
    location_score: float,
) -> float:
    """
    Calculate the raw V2 score and apply mismatch caps.

    Caps are essential: otherwise a job with excellent keyword
    overlap can outrank a job that actually matches the candidate's
    target career.
    """

    raw_score = (
        skill_score * SKILL_WEIGHT
        + role_score * ROLE_WEIGHT
        + experience_score * EXPERIENCE_WEIGHT
        + location_score * LOCATION_WEIGHT
    )

    # --------------------------------------------------------
    # Role caps
    # --------------------------------------------------------

    if role_score < 40:
        raw_score = min(raw_score, 50.0)

    elif role_score < 60:
        raw_score = min(raw_score, 65.0)

    elif role_score < 75:
        raw_score = min(raw_score, 78.0)

    # --------------------------------------------------------
    # Experience caps
    # --------------------------------------------------------

    if experience_score < 20:
        raw_score = min(raw_score, 50.0)

    elif experience_score < 40:
        raw_score = min(raw_score, 60.0)

    elif experience_score < 60:
        raw_score = min(raw_score, 72.0)

    return round(
        max(0.0, min(100.0, raw_score)),
        2,
    )


# ------------------------------------------------------------
# Individual job
# ------------------------------------------------------------

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
        skill_score=round(skill_score, 2),
        role_score=round(role_score, 2),
        experience_score=round(experience_score, 2),
        location_score=round(location_score, 2),
        final_score=final_score,
        eligibility_reasons=eligibility.reasons,
    )


# ------------------------------------------------------------
# Ranking
# ------------------------------------------------------------

def rank_jobs(
    candidate: CandidateProfile,
    jobs: list[Job],
) -> list[JobMatch]:
    """
    Score all jobs and return eligible jobs from highest to lowest.
    """

    matches = [
        score_job(candidate, job)
        for job in jobs
    ]

    eligible_matches = [
        match
        for match in matches
        if match.eligible
    ]

    return sorted(
        eligible_matches,
        key=lambda match: match.final_score,
        reverse=True,
    )
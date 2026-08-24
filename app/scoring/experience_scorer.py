"""
Experience scoring utilities.

Scores how well a candidate's experience matches
the experience level required by a job.

The scorer is intentionally flexible:
- Missing requirements are neutral.
- Meeting the requirement gives a strong score.
- Slightly under-qualified candidates are not crushed.
- Large experience gaps are penalized progressively.
- The job's seniority wording can influence the score.
"""

import re

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.services.experience_parser import parse_experience_years


def _clean(value) -> str:
    """Normalize text safely."""
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip().lower(),
    )


def _detect_seniority(job: Job) -> str:
    """
    Detect broad seniority from job title and experience text.

    Returns one of:
    - intern
    - entry
    - junior
    - mid
    - senior
    - staff
    - lead
    - unknown
    """

    title = _clean(getattr(job, "title", ""))
    experience = _clean(
        getattr(job, "experience_required", "")
    )

    text = f"{title} {experience}"

    # --------------------------------------------------------
    # Internship / student roles
    # --------------------------------------------------------

    if re.search(
        r"\b(intern|internship|trainee|student)\b",
        text,
    ):
        return "intern"

    # --------------------------------------------------------
    # Staff / principal
    # --------------------------------------------------------

    if re.search(
        r"\b(principal|staff|distinguished)\b",
        text,
    ):
        return "staff"

    # --------------------------------------------------------
    # Lead / manager
    # --------------------------------------------------------

    if re.search(
        r"\b(lead|manager|head of|director)\b",
        text,
    ):
        return "lead"

    # --------------------------------------------------------
    # Senior
    # --------------------------------------------------------

    if re.search(
        r"\b(senior|sr\.?|sr)\b",
        text,
    ):
        return "senior"

    # --------------------------------------------------------
    # Junior
    # --------------------------------------------------------

    if re.search(
        r"\b(junior|jr\.?|jr)\b",
        text,
    ):
        return "junior"

    # --------------------------------------------------------
    # Entry level
    # --------------------------------------------------------

    if re.search(
        r"\b(entry[- ]level|graduate|fresher|new grad|associate)\b",
        text,
    ):
        return "entry"

    # --------------------------------------------------------
    # Generic software/engineering role
    # --------------------------------------------------------

    return "mid"


def calculate_experience_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate experience compatibility.

    Returns a score between 0 and 100.

    Important:
    This is NOT a strict mathematical requirement checker.

    A candidate who is slightly below a requirement can still
    receive a strong score because real-world job requirements
    are often flexible.
    """

    candidate_years = max(
        float(candidate.experience_years or 0.0),
        0.0,
    )

    required_years = parse_experience_years(
        getattr(job, "experience_required", None)
    )

    seniority = _detect_seniority(job)

    # ========================================================
    # Internship / trainee roles
    # ========================================================

    if seniority == "intern":
        # An experienced candidate is not a natural match
        # for an internship, even if they technically qualify.
        if candidate_years <= 0.5:
            return 100.0

        if candidate_years <= 1.0:
            return 70.0

        if candidate_years <= 2.0:
            return 40.0

        return 20.0

    # ========================================================
    # No explicit numeric requirement
    # ========================================================

    if required_years is None:
        if seniority == "entry":
            if candidate_years <= 1.5:
                return 100.0

            if candidate_years <= 3.0:
                return 80.0

            return 60.0

        if seniority == "junior":
            if candidate_years <= 2.0:
                return 100.0

            if candidate_years <= 3.0:
                return 90.0

            return 75.0

        if seniority == "senior":
            if candidate_years >= 3.0:
                return 90.0

            if candidate_years >= 2.0:
                return 70.0

            return 50.0

        if seniority in {"staff", "lead"}:
            if candidate_years >= 5.0:
                return 90.0

            if candidate_years >= 3.0:
                return 65.0

            return 40.0

        # Generic role with no explicit requirement.
        return 70.0

    # ========================================================
    # Defensive handling
    # ========================================================

    if required_years <= 0:
        return 70.0

    # ========================================================
    # Candidate meets requirement
    # ========================================================

    if candidate_years >= required_years:
        # Don't automatically give 100 to massively
        # overqualified candidates.
        excess_ratio = (
            candidate_years / required_years
        )

        if excess_ratio <= 1.5:
            return 100.0

        if excess_ratio <= 2.5:
            return 90.0

        return 80.0

    # ========================================================
    # Candidate is below requirement
    # ========================================================

    gap = required_years - candidate_years

    # Slightly under the requirement.
    if gap <= 1.0:
        return 85.0

    # Moderately under.
    if gap <= 2.0:
        return 70.0

    # Significant gap.
    if gap <= 3.0:
        return 55.0

    # Large gap.
    if gap <= 5.0:
        return 35.0

    # Very large gap.
    return 20.0
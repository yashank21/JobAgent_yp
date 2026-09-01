"""
Experience compatibility scoring.

General-purpose candidate-driven experience scoring.

Rules:
- Numeric job requirements are the strongest signal.
- Meeting or exceeding the requirement = 100.
- Partial experience receives a proportional score.
- No experience for a positive requirement = 0.
- If no numeric requirement exists, job seniority is used as a
  broad fallback.
- No candidate-specific thresholds are hardcoded.

Experience intelligence:
- Internship experience is tracked separately when available.
- Requirement strictness is classified from job text.
- Experience risk is an explainable warning, not a ranking penalty.
- Experience mismatch is NEVER a hard eligibility rejection.
"""

import re

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.services.experience_parser import (
    classify_requirement_strictness,
    parse_experience_years,
)


def _clean(value: object) -> str:
    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip().lower(),
    )


def _candidate_years(candidate: CandidateProfile) -> float:
    try:
        return max(
            float(
                getattr(
                    candidate.facts,
                    "experience_years",
                    0.0,
                )
                or 0.0
            ),
            0.0,
        )
    except (TypeError, ValueError):
        return 0.0


def _candidate_internship_years(
    candidate: CandidateProfile,
) -> float | None:
    """Return internship years if explicitly provided, else None."""
    value = getattr(
        candidate.facts,
        "internship_years",
        None,
    )
    if value is None:
        return None
    try:
        result = float(value)
        return max(result, 0.0)
    except (TypeError, ValueError):
        return None


def _relevant_experience_years(
    candidate: CandidateProfile,
) -> float:
    """
    Compute relevant experience for scoring purposes.

    Uses total professional experience (experience_years).
    Internship years are tracked separately and available
    for explanation but do NOT automatically substitute for
    professional experience in the numeric score.

    This preserves the distinction that not every recruiter
    counts internships as professional experience.
    """
    return _candidate_years(candidate)


# ============================================================
# EXPERIENCE RISK
# ============================================================

# Controlled vocabulary for experience screening risk.
#
# This is an EXPLANATION signal, NOT a ranking penalty.
# Risk does NOT directly modify ranking_score.
#
# LOW     = meets or exceeds requirement
# MEDIUM  = slightly below requirement
# HIGH    = substantially below requirement
# UNKNOWN = requirement or experience unknown


def classify_experience_risk(
    candidate_years: float,
    required_years: float | None,
    strictness: str,
) -> str:
    """
    Classify experience screening risk.

    This is an explainable warning, not a hidden ranking modifier.

    Risk is based on:
    - Gap between candidate experience and job requirement
    - How strictly the requirement is worded

    Conservative原则:
    - When information is insufficient, return UNKNOWN
    - Never claim to predict recruiter behavior
    - Use language like "may be a screening risk"
    """

    if required_years is None or required_years <= 0:
        return "unknown"

    if candidate_years >= required_years:
        return "low"

    gap = required_years - candidate_years
    gap_ratio = gap / required_years if required_years > 0 else 0

    if strictness == "strict":
        if gap_ratio <= 0.25:
            return "medium"
        return "high"

    if strictness == "required":
        if gap_ratio <= 0.25:
            return "low"
        if gap_ratio <= 0.50:
            return "medium"
        return "high"

    if strictness == "preferred":
        if gap_ratio <= 0.50:
            return "low"
        return "medium"

    # Unknown strictness: assume moderate risk
    if gap_ratio <= 0.25:
        return "low"
    if gap_ratio <= 0.50:
        return "medium"
    return "high"


def _detect_seniority(job: Job) -> str:
    """
    Determine job seniority from enriched metadata or job text.
    """

    seniority = _clean(
        getattr(job, "seniority", "")
    )

    confidence = float(
        getattr(
            job,
            "ai_confidence",
            0.0,
        )
        or 0.0
    )

    if (
        seniority
        and seniority != "unknown"
        and confidence >= 0.60
    ):
        return seniority

    title = _clean(
        getattr(job, "title", "")
    )

    experience = _clean(
        getattr(job, "experience_required", "")
    )

    text = f"{title} {experience}"

    patterns = (
        (
            "director",
            r"\b(director|vp|vice president|head of)\b",
        ),
        (
            "manager",
            r"\b(manager|engineering manager|people manager)\b",
        ),
        (
            "principal",
            r"\b(principal|distinguished)\b",
        ),
        (
            "staff",
            r"\bstaff\b",
        ),
        (
            "lead",
            r"\b(lead|tech lead|technical lead)\b",
        ),
        (
            "senior",
            r"\b(senior|sr\.?)\b",
        ),
        (
            "intern",
            r"\b(intern|internship|trainee)\b",
        ),
        (
            "entry",
            r"\b(entry[- ]level|graduate|fresher|new grad)\b",
        ),
        (
            "junior",
            r"\b(junior|jr\.?)\b",
        ),
        (
            "mid",
            r"\b(mid[- ]level|mid)\b",
        ),
    )

    for level, pattern in patterns:
        if re.search(pattern, text):
            return level

    return "unknown"


def _required_years(job: Job) -> float | None:
    """
    Extract the most reliable numeric experience requirement.
    """

    explicit = getattr(
        job,
        "experience_years_required",
        None,
    )

    if explicit is not None:
        try:
            value = float(explicit)

            if value > 0:
                return value

        except (TypeError, ValueError):
            pass

    for field_name in (
        "experience_required",
        "description",
    ):
        text = getattr(
            job,
            field_name,
            "",
        ) or ""

        parsed = parse_experience_years(text)

        if parsed is not None and parsed > 0:
            return float(parsed)

    return None


def _numeric_experience_score(
    candidate_years: float,
    required_years: float,
) -> float:
    """
    Score candidate experience against an explicit requirement.

    The score is proportional to the candidate's experience until
    the requirement is met.
    """

    if required_years <= 0:
        return 100.0

    if candidate_years <= 0:
        return 0.0

    if candidate_years >= required_years:
        return 100.0

    return round(
        (candidate_years / required_years) * 100,
        2,
    )


def _seniority_experience_score(
    candidate_years: float,
    seniority: str,
) -> float:
    """
    Fallback scoring when no numeric requirement exists.

    These are broad industry-oriented experience bands rather than
    thresholds tied to a particular candidate.
    """

    if seniority == "intern":
        if candidate_years <= 1.0:
            return 100.0
        return 80.0

    if seniority == "entry":
        if candidate_years <= 2.0:
            return 100.0
        return 90.0

    if seniority == "junior":
        if candidate_years <= 2.0:
            return 100.0
        if candidate_years <= 4.0:
            return 90.0
        return 80.0

    if seniority == "mid":
        if candidate_years >= 2.0:
            return 100.0
        if candidate_years > 0:
            return 50.0
        return 0.0

    if seniority == "senior":
        if candidate_years >= 5.0:
            return 100.0
        if candidate_years >= 3.0:
            return 80.0
        if candidate_years > 0:
            return 40.0
        return 0.0

    if seniority == "lead":
        if candidate_years >= 7.0:
            return 100.0
        if candidate_years >= 5.0:
            return 75.0
        if candidate_years > 0:
            return 35.0
        return 0.0

    if seniority == "staff":
        if candidate_years >= 8.0:
            return 100.0
        if candidate_years >= 6.0:
            return 75.0
        if candidate_years > 0:
            return 30.0
        return 0.0

    if seniority == "principal":
        if candidate_years >= 10.0:
            return 100.0
        if candidate_years >= 8.0:
            return 75.0
        if candidate_years > 0:
            return 25.0
        return 0.0

    if seniority == "manager":
        if candidate_years >= 7.0:
            return 100.0
        if candidate_years >= 5.0:
            return 75.0
        if candidate_years > 0:
            return 30.0
        return 0.0

    if seniority == "director":
        if candidate_years >= 10.0:
            return 100.0
        if candidate_years >= 8.0:
            return 75.0
        if candidate_years > 0:
            return 25.0
        return 0.0

    # Unknown seniority means there is insufficient evidence
    # to penalize the candidate.
    return 100.0


def calculate_experience_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate candidate-job experience compatibility from 0 to 100.

    Priority:

        1. Explicit numeric requirement
        2. Parsed numeric requirement
        3. Job seniority
        4. Unknown -> neutral/full score
    """

    candidate_years = _candidate_years(candidate)

    required_years = _required_years(job)

    if required_years is not None:
        return _numeric_experience_score(
            candidate_years,
            required_years,
        )

    seniority = _detect_seniority(job)

    return round(
        _seniority_experience_score(
            candidate_years,
            seniority,
        ),
        2,
    )
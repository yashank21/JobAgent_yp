"""
Seniority parsing utilities.

Determines normalized seniority primarily from the job title
and secondarily from an already-parsed experience requirement.
"""

import re


def parse_seniority(
    title: str,
    experience_years: float | None = None,
) -> str:
    """
    Return normalized seniority.

    Possible values:
        intern
        junior
        mid
        senior
        lead
        staff
        principal
        unknown

    Explicit title seniority always takes priority.
    Experience is used only when the title has no
    explicit seniority marker.
    """

    title_lower = (
        title or ""
    ).lower().strip()

    # ---------------------------------------------------------
    # Explicit title-based seniority
    # ---------------------------------------------------------

    if re.search(
        r"\bprincipal\b",
        title_lower,
    ):
        return "principal"

    if re.search(
        r"\bstaff\b",
        title_lower,
    ):
        return "staff"

    if re.search(
        r"\b(?:tech(?:nical)?\s+)?lead\b",
        title_lower,
    ):
        return "lead"

    if re.search(
        r"\bsenior\b|\bsr\.?\b",
        title_lower,
    ):
        return "senior"

    if re.search(
        r"\bjunior\b|\bjr\.?\b",
        title_lower,
    ):
        return "junior"

    if re.search(
        r"\bintern(ship)?\b",
        title_lower,
    ):
        return "intern"

    # ---------------------------------------------------------
    # Experience-based inference
    # ---------------------------------------------------------

    if experience_years is None:
        return "unknown"

    try:
        years = float(experience_years)
    except (TypeError, ValueError):
        return "unknown"

    if years >= 8:
        return "senior"

    if years >= 4:
        return "mid"

    if years >= 1:
        return "junior"

    return "unknown"
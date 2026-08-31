"""
Resume classification utilities.

Converts extracted resume text into structured candidate signals.

This module is intentionally deterministic for v1.
It does NOT infer user intent or modify preferred_roles.
"""

import re
from dataclasses import dataclass, field

from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
)
from app.services.seniority_parser import parse_seniority
from app.services.skill_extractor import extract_skills


# ============================================================
# RESULT MODEL
# ============================================================


@dataclass
class ResumeClassification:

    skills: list[str] = field(
        default_factory=list
    )

    role_families: list[str] = field(
        default_factory=list
    )

    role_titles: list[str] = field(
        default_factory=list
    )

    experience_years: float = 0.0

    career_level: str = "unknown"


# ============================================================
# EXPERIENCE EXTRACTION
# ============================================================


def _extract_experience_years(text: str) -> float:
    """
    Estimate professional experience from resume text.

    Strategy:
        1. Prefer explicit experience statements.
        2. Otherwise extract employment date ranges.
        3. Handle Present/current employment.
    """

    if not text:
        return 0.0

    normalized = re.sub(
        r"\s+",
        " ",
        text.lower(),
    )

    # --------------------------------------------------------
    # 1. Explicit experience statements
    # --------------------------------------------------------

    patterns = [
        (
            r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+"
            r"(?:of\s+)?(?:professional\s+)?experience",
            1.0,
        ),
        (
            r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+"
            r"(?:of\s+)?experience",
            1.0,
        ),
        (
            r"(\d+(?:\.\d+)?)\s*\+?\s*months?\s+"
            r"(?:of\s+)?(?:professional\s+)?experience",
            1 / 12,
        ),
    ]

    explicit_values = []

    for pattern, multiplier in patterns:

        for match in re.finditer(
            pattern,
            normalized,
        ):
            try:
                value = float(match.group(1))
                explicit_values.append(
                    value * multiplier
                )
            except ValueError:
                continue

    if explicit_values:
        return round(
            max(explicit_values),
            2,
        )

    # --------------------------------------------------------
    # Month names
    #
    # IMPORTANT:
    # All month alternatives are NON-CAPTURING.
    # This prevents group-number bugs.
    # --------------------------------------------------------

    month_pattern = (
        r"(?:"
        r"jan(?:uary)?|"
        r"feb(?:ruary)?|"
        r"mar(?:ch)?|"
        r"apr(?:il)?|"
        r"may|"
        r"jun(?:e)?|"
        r"jul(?:y)?|"
        r"aug(?:ust)?|"
        r"sep(?:t(?:ember)?)?|"
        r"oct(?:ober)?|"
        r"nov(?:ember)?|"
        r"dec(?:ember)?"
        r")"
    )

    month_map = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }

    durations = []

    # --------------------------------------------------------
    # 2. Completed employment ranges
    #
    # Example:
    # June 2025 – May 2026
    # --------------------------------------------------------

    date_range_pattern = re.compile(
        rf"({month_pattern})\s+(\d{{4}})"
        rf"\s*(?:-|–|—|to)\s*"
        rf"({month_pattern})\s+(\d{{4}})",
        re.IGNORECASE,
    )

    for match in date_range_pattern.finditer(
        normalized
    ):

        start_month = month_map[
            match.group(1).lower()
        ]

        start_year = int(
            match.group(2)
        )

        end_month = month_map[
            match.group(3).lower()
        ]

        end_year = int(
            match.group(4)
        )

        start_total = (
            start_year * 12
            + start_month
        )

        end_total = (
            end_year * 12
            + end_month
        )

        if end_total < start_total:
            continue

        months = (
            end_total
            - start_total
            + 1
        )

        durations.append(
            months / 12
        )

    # --------------------------------------------------------
    # 3. Current / Present employment
    #
    # Example:
    # June 2025 – Present
    # --------------------------------------------------------

    present_pattern = re.compile(
        rf"({month_pattern})\s+(\d{{4}})"
        rf"\s*(?:-|–|—|to)\s*"
        r"(present|current)",
        re.IGNORECASE,
    )

    from datetime import datetime

    now = datetime.now()

    for match in present_pattern.finditer(
        normalized
    ):

        start_month = month_map[
            match.group(1).lower()
        ]

        start_year = int(
            match.group(2)
        )

        start_total = (
            start_year * 12
            + start_month
        )

        current_total = (
            now.year * 12
            + now.month
        )

        if current_total >= start_total:

            months = (
                current_total
                - start_total
                + 1
            )

            durations.append(
                months / 12
            )

    if not durations:
        return 0.0

    return round(
        max(durations),
        2,
    )


# ============================================================
# ROLE TITLE EXTRACTION
# ============================================================


_ROLE_TITLE_PATTERNS = [
    r"\b(?:software|machine learning|ml|ai|data|backend|"
    r"frontend|devops|research|mobile|llm|genai|"
    r"platform|cloud|support|customer|integration|"
    r"rpa)\s+(?:engineer|developer|scientist|"
    r"researcher|analyst)\b",

    r"\bsoftware development engineer\b",

    r"\b(?:sde|mle|swe)\b",
]


def _extract_role_titles(text: str) -> list[str]:
    """
    Extract likely professional role titles from resume text.

    Role titles are treated as resume evidence, not user intent.

    The extractor recognizes common AI/ML/software roles and
    preserves seniority markers when present.
    """

    if not text:
        return []

    normalized = re.sub(
        r"\s+",
        " ",
        text.lower(),
    )

    # ---------------------------------------------------------
    # Role vocabulary
    # ---------------------------------------------------------

    role_pattern = (
        r"\b("
        r"(?:ai|artificial intelligence)\s*(?:/|and)?\s*"
        r"(?:ml|machine learning)?\s+"
        r"(?:engineer|developer|scientist)"
        r"|"
        r"machine learning\s+engineer"
        r"|"
        r"ml\s+engineer"
        r"|"
        r"software\s+(?:engineering|development)\s+"
        r"(?:intern|engineer|developer)"
        r"|"
        r"software\s+engineer"
        r"|"
        r"backend\s+engineer"
        r"|"
        r"frontend\s+engineer"
        r"|"
        r"data\s+scientist"
        r"|"
        r"data\s+engineer"
        r"|"
        r"data\s+analyst"
        r"|"
        r"devops\s+engineer"
        r"|"
        r"research\s+engineer"
        r"|"
        r"researcher"
        r"|"
        r"llm\s+engineer"
        r"|"
        r"genai\s+engineer"
        r"|"
        r"ai\s+engineer"
        r"|"
        r"computer\s+vision\s+engineer"
        r"|"
        r"nlp\s+engineer"
        r")\b"
    )

    seniority_pattern = (
        r"\b("
        r"intern|internship|junior|jr\.?|"
        r"senior|sr\.?|staff|principal|lead"
        r")\b"
    )

    found = []

    # ---------------------------------------------------------
    # Search role titles
    # ---------------------------------------------------------

    for match in re.finditer(
        role_pattern,
        normalized,
        re.IGNORECASE,
    ):

        title = match.group(1).strip()

        # -----------------------------------------------------
        # Check immediately before the title for seniority.
        # -----------------------------------------------------

        prefix = normalized[
            max(
                0,
                match.start() - 30,
            ):
            match.start()
        ]

        seniority_match = re.search(
            seniority_pattern + r"\s*$",
            prefix,
            re.IGNORECASE,
        )

        if seniority_match:
            title = (
                seniority_match.group(1)
                + " "
                + title
            )

        # -----------------------------------------------------
        # Check immediately after the title for internship.
        # -----------------------------------------------------

        suffix = normalized[
            match.end():
            match.end() + 20
        ]

        intern_match = re.match(
            r"\s*(intern|internship)\b",
            suffix,
            re.IGNORECASE,
        )

        if intern_match:
            title = (
                title
                + " "
                + intern_match.group(1)
            )

        title = re.sub(
            r"\s+",
            " ",
            title,
        ).strip()

        if title not in found:
            found.append(title)

    return found


# ============================================================
# ROLE FAMILY EXTRACTION
# ============================================================


def _extract_role_families(
    role_titles: list[str],
) -> list[str]:
    """
    Classify extracted role titles into role families.
    """

    families = []

    for title in role_titles:

        family = classify_role(title)

        if family == RoleFamily.UNKNOWN:
            continue

        value = family.value

        if value not in families:
            families.append(value)

    return families


# ============================================================
# CAREER LEVEL
# ============================================================


def _extract_career_level(
    role_titles: list[str],
    experience_years: float,
) -> str:
    """
    Determine candidate career level.

    Explicit title seniority is preferred.

    Experience is used only as a fallback.
    """

    priority = [
        "principal",
        "staff",
        "lead",
        "senior",
        "junior",
        "intern",
    ]

    detected = []

    for title in role_titles:

        level = parse_seniority(
            title,
            experience_years=None,
        )

        if level != "unknown":
            detected.append(level)

    for level in priority:

        if level in detected:
            return level

    # Fallback to experience inference.

    return parse_seniority(
        "",
        experience_years=experience_years,
    )


# ============================================================
# PUBLIC API
# ============================================================


def classify_resume(
    resume_text: str,
) -> ResumeClassification:
    """
    Convert resume text into structured candidate signals.
    """

    if not resume_text:
        return ResumeClassification()

    skills = extract_skills(
        resume_text,
    )

    role_titles = _extract_role_titles(
        resume_text,
    )

    role_families = _extract_role_families(
        role_titles,
    )

    experience_years = _extract_experience_years(
        resume_text,
    )

    career_level = _extract_career_level(
        role_titles,
        experience_years,
    )

    return ResumeClassification(
        skills=skills,
        role_families=role_families,
        role_titles=role_titles,
        experience_years=experience_years,
        career_level=career_level,
    )
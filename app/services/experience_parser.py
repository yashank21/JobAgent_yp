"""
Experience parsing utilities.

Extracts minimum years of experience from job-description text.
"""

import re


# ============================================================
# REQUIREMENT STRICTNESS
# ============================================================

# Controlled vocabulary for how strictly the requirement
# is likely enforced.
#
# UNKNOWN  = ambiguous or missing wording
# PREFERRED = nice-to-have, unlikely hard filter
# REQUIRED = standard requirement, may be flexible
# STRICT  = explicitly enforced, high screening risk

_STRICT_PATTERNS = [
    r"\bmust\s+have\b",
    r"\brequired\b",
    r"\bmandatory\b",
    r"\bessential\b",
    r"\bnon[- ]?negotiable\b",
    r"\bonly\s+candidates?\s+with\b",
    r"\bminimum\s+of\b",
]

_PREFERRED_PATTERNS = [
    r"\bpreferred\b",
    r"\bdesirable\b",
    r"\bnice[- ]to[- ]have\b",
    r"\bplus\b",
    r"\badvantageous\b",
    r"\bideal\b",
    r"\bwould\s+be\s+(?:a\s+)?(?:bonus|plus|advantage)\b",
]


def classify_requirement_strictness(
    experience_text: str,
) -> str:
    """
    Classify how strictly the experience requirement is worded.

    Returns one of: "unknown", "preferred", "required", "strict"

    This is a conservative, explainable classification.
    It does NOT predict recruiter behavior — it classifies
    the stated wording only.
    """

    if not experience_text:
        return "unknown"

    text = experience_text.lower().strip()

    for pattern in _STRICT_PATTERNS:
        if re.search(pattern, text):
            return "strict"

    for pattern in _PREFERRED_PATTERNS:
        if re.search(pattern, text):
            return "preferred"

    # If a numeric requirement exists but no strictness keyword,
    # treat as standard "required".
    parsed = parse_experience_years(text)
    if parsed is not None and parsed > 0:
        return "required"

    return "unknown"


def parse_experience_years(text: str) -> float | None:
    """
    Extract the minimum required experience from text.

    Examples:
        "2+ years of experience" -> 2.0
        "3 years of experience" -> 3.0
        "1-3 years of experience" -> 1.0
        "5+ years software development experience" -> 5.0
        "11 months of experience" -> 0.9167
        "6+ months of experience" -> 0.5

    Returns None when no experience requirement can be detected.
    """

    if not text:
        return None

    text_lower = text.lower()

    # ---------------------------------
    # Month-based experience
    # ---------------------------------

    month_patterns = [
        # "6+ months"
        r"(\d+(?:\.\d+)?)\s*\+\s*months?",

        # "11 months of experience"
        r"(\d+(?:\.\d+)?)\s*months?\s+(?:of\s+)?experience",
    ]

    for pattern in month_patterns:
        match = re.search(pattern, text_lower)

        if match:
            months = float(match.group(1))
            return months / 12

    # ---------------------------------
    # Year-based experience
    # ---------------------------------

    year_patterns = [
        # "2+ years"
        r"(\d+(?:\.\d+)?)\s*\+\s*years?",

        # "1-3 years" / "1 to 3 years"
        r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*\d+(?:\.\d+)?\s*years?",

        # Unicode en-dash ranges such as "1–2 years".
        r"(\d+(?:\.\d+)?)\s*–\s*\d+(?:\.\d+)?\s*years?",

        # "2 years of experience"
        r"(\d+(?:\.\d+)?)\s*years?\s+(?:of\s+)?(?:experience|exp)\b",

        # Possessive form: "3 years' experience".
        r"(\d+(?:\.\d+)?)\s*years?['’]\s*experience\b",
    ]

    for pattern in year_patterns:
        match = re.search(pattern, text_lower)

        if match:
            return float(match.group(1))

    return None

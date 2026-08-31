"""
Experience parsing utilities.

Extracts minimum years of experience from job-description text.
"""

import re


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

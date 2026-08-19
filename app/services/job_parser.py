"""
Job description parsing utilities.
"""

import re


def extract_section(
    text: str,
    section: str,
    next_sections: list[str],
) -> str:
    """
    Extract a section from a normalized job description.

    Example:

        BASIC QUALIFICATIONS:
        Bachelor's degree...
        2+ years experience...

        PREFERRED SKILLS:
        Python...
        C++...

    Returns only the requested section content.
    """

    if not text:
        return ""

    section_pattern = re.escape(section)

    next_pattern = "|".join(
        re.escape(item)
        for item in next_sections
    )

    pattern = (
        rf"{section_pattern}\s*:?"
        rf"(.*?)(?="
        rf"(?:{next_pattern})\s*:?"
        rf"|$)"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return ""

    return match.group(1).strip()
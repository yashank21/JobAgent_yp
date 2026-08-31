"""
Text cleaning utilities.
"""

import html
import re


def clean_html(raw_html: str) -> str:
    """
    Convert HTML content into readable plain text.
    """

    if not raw_html:
        return ""

    text = html.unescape(raw_html)

    text = re.sub(r"<[^>]+>", " ", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()

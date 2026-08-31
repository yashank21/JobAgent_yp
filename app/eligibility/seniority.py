"""
Seniority detection utilities.
"""

import re


SENIORITY_PATTERNS = {
    "intern": [
        r"\bintern(ship)?\b",
    ],
    "entry": [
        r"\bentry[- ]level\b",
        r"\bjunior\b",
        r"\bgraduate\b",
        r"\bnew grad\b",
        r"\bnew graduate\b",
        r"\bassociate engineer\b",
    ],
    "mid": [
        r"\bsoftware engineer\b",
        r"\bsoftware developer\b",
        r"\bbackend engineer\b",
        r"\bbackend developer\b",
        r"\bai engineer\b",
        r"\bml engineer\b",
        r"\bmachine learning engineer\b",
        r"\bdata scientist\b",
        r"\bresearch engineer\b",
        r"\bapplied scientist\b",
    ],
    "senior": [
        r"\bsenior\b",
        r"\bsr\.?\b",
        r"\bstaff\b",
        r"\bprincipal\b",
        r"\blead engineer\b",
        r"\btech lead\b",
    ],
    "manager": [
        r"\bengineering manager\b",
        r"\bmanager\b",
        r"\bdirector\b",
        r"\bhead of\b",
        r"\bvp\b",
        r"\bvice president\b",
    ],
}


def classify_seniority(title: str) -> str:
    """
    Classify job seniority from title.
    """

    title = (title or "").lower()

    # Managerial roles first.
    for pattern in SENIORITY_PATTERNS["manager"]:
        if re.search(pattern, title):
            return "manager"

    for pattern in SENIORITY_PATTERNS["senior"]:
        if re.search(pattern, title):
            return "senior"

    for pattern in SENIORITY_PATTERNS["intern"]:
        if re.search(pattern, title):
            return "intern"

    for pattern in SENIORITY_PATTERNS["entry"]:
        if re.search(pattern, title):
            return "entry"

    for pattern in SENIORITY_PATTERNS["mid"]:
        if re.search(pattern, title):
            return "mid"

    return "unknown"

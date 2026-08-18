"""
Location normalization utilities.

Converts raw job-location strings into broad normalized
location categories used by the eligibility system.
"""

import re

INDIA_MARKERS = {
    "india", "bengaluru", "bangalore", "pune", "mumbai", "hyderabad",
    "delhi", "new delhi", "gurugram", "gurgaon", "noida", "chennai",
    "kolkata", "ahmedabad", "indore", "jaipur", "chandigarh", "kochi",
    "thiruvananthapuram", "bhubaneswar", "mysuru", "mysore",
}

# Strict 2-letter state codes (excluding 'in' to avoid collision with India)
US_STATE_CODES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id",
    "il", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms",
    "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok",
    "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv",
    "wi", "wy", "dc",
}

# Explicit multi-word US cities and phrases
US_EXPLICIT_PHRASES = [
    "united states", "usa", "u.s.", "hawthorne", "redmond", "starbase",
    "bastrop", "los angeles", "seattle", "austin", "boston", "new york",
    "san francisco", "mountain view", "menlo park", "palo alto", "san diego",
    "irvine", "remote - us", "remote - usa", "us-remote", "us remote"
]

# Word boundary regex for US state codes (e.g. "Austin, TX" or "CA")
US_STATE_PATTERN = re.compile(
    r'\b(' + '|'.join(US_STATE_CODES).upper() + r')\b', 
    re.IGNORECASE
)

# Word boundary regex for standalone "US" or "USA"
US_COUNTRY_PATTERN = re.compile(r'\b(US|USA)\b', re.IGNORECASE)


def _clean(value: str) -> str:
    """Normalize whitespace and casing."""
    value = value.strip().lower()
    return re.sub(r"\s+", " ", value)


def normalize_location(location: str) -> str:
    """
    Normalize location string into standard buckets:
    - 'India'
    - 'United States'
    - 'Remote' (Worldwide)
    - Original cleaned location string
    """
    if not location:
        return "Unknown"

    val_clean = _clean(location)

    # 1. Check explicit India locations first
    if any(marker in val_clean for marker in INDIA_MARKERS):
        return "India"

    # 2. Check for explicit US markers using word boundaries
    if (
        any(phrase in val_clean for phrase in US_EXPLICIT_PHRASES)
        or US_STATE_PATTERN.search(location)
        or US_COUNTRY_PATTERN.search(location)
    ):
        return "United States"

    # 3. Handle Remote / Distributed
    if any(remote_kw in val_clean for remote_kw in ["remote", "distributed", "work from home"]):
        return "Remote"

    return location.strip()


def location_matches(
    job_location: str,
    preferred_locations: list[str],
) -> bool:
    """
    Determine whether a job location matches candidate preferred locations.
    """
    if not preferred_locations:
        return True

    normalized_job = normalize_location(job_location)

    for preferred in preferred_locations:
        normalized_pref = normalize_location(preferred)

        # Direct exact match (e.g., "India" == "India")
        if normalized_job == normalized_pref:
            return True

        # Candidate wanting India can accept worldwide Remote roles
        if normalized_job == "Remote" and normalized_pref in ["India", "Remote"]:
            return True

        # Fallback substring match for specific city preferences
        if normalized_pref.lower() in job_location.lower():
            return True

    return False
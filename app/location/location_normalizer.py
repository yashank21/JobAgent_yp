"""
Location normalization utilities.

Converts raw job-location strings into normalized
location categories used by the eligibility system.
"""

import re


INDIA_MARKERS = {
    "india",
    "bengaluru",
    "bangalore",
    "pune",
    "mumbai",
    "hyderabad",
    "delhi",
    "new delhi",
    "gurugram",
    "gurgaon",
    "noida",
    "chennai",
    "kolkata",
    "ahmedabad",
    "indore",
    "jaipur",
    "chandigarh",
    "kochi",
    "thiruvananthapuram",
    "bhubaneswar",
    "mysuru",
    "mysore",
}


US_STATE_CODES = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de",
    "fl", "ga", "hi", "id", "il", "ia", "ks", "ky",
    "la", "me", "md", "ma", "mi", "mn", "ms", "mo",
    "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc",
    "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd",
    "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi",
    "wy", "dc",
}


US_EXPLICIT_PHRASES = [
    "united states",
    "usa",
    "u.s.",
    "hawthorne",
    "redmond",
    "starbase",
    "bastrop",
    "los angeles",
    "seattle",
    "austin",
    "boston",
    "new york",
    "san francisco",
    "mountain view",
    "menlo park",
    "palo alto",
    "san diego",
    "irvine",
    "remote - us",
    "remote - usa",
    "us-remote",
    "us remote",
]


US_STATE_PATTERN = re.compile(
    r"\b(" + "|".join(US_STATE_CODES) + r")\b",
    re.IGNORECASE,
)


US_COUNTRY_PATTERN = re.compile(
    r"\b(US|USA)\b",
    re.IGNORECASE,
)


REMOTE_PATTERNS = [
    r"\bremote\b",
    r"\bdistributed\b",
    r"\bwork\s+from\s+home\b",
    r"\bwork\s+remotely\b",
    r"\bfully\s+remote\b",
]


def _clean(value: str) -> str:
    """Normalize whitespace and casing."""

    value = value.strip().lower()

    return re.sub(
        r"\s+",
        " ",
        value,
    )


def _contains_india(value: str) -> bool:
    """Return True when the location clearly refers to India."""

    return any(
        marker in value
        for marker in INDIA_MARKERS
    )


def _contains_us(value: str) -> bool:
    """Return True when the location clearly refers to the US."""

    return (
        any(
            phrase in value
            for phrase in US_EXPLICIT_PHRASES
        )
        or bool(US_STATE_PATTERN.search(value))
        or bool(US_COUNTRY_PATTERN.search(value))
    )


def _is_remote(value: str) -> bool:
    """Return True when the location describes remote work."""

    return any(
        re.search(
            pattern,
            value,
            re.IGNORECASE,
        )
        for pattern in REMOTE_PATTERNS
    )


def normalize_location(location: str) -> str:
    """
    Normalize a raw location into a broad category.

    Possible values:

        India
        Remote
        United States
        Unknown
        <specific location>

    Remote locations are intentionally normalized to "Remote".
    Country-specific remote eligibility is handled separately
    by location_matches().
    """

    if not location:
        return "Unknown"

    value = _clean(location)

    is_remote = _is_remote(value)
    is_india = _contains_india(value)
    is_us = _contains_us(value)

    # --------------------------------------------------------
    # 1. Remote
    # --------------------------------------------------------
    #
    # Keep ALL remote locations as "Remote".
    #
    # Examples:
    #
    # Remote
    # Remote - India
    # Remote - United States
    # Remote, United Kingdom
    #
    # All normalize to:
    #
    # Remote
    #
    # This preserves the existing API/test contract.
    #

    if is_remote:
        return "Remote"

    # --------------------------------------------------------
    # 2. Physical India location
    # --------------------------------------------------------

    if is_india:
        return "India"

    # --------------------------------------------------------
    # 3. Physical US location
    # --------------------------------------------------------

    if is_us:
        return "United States"

    # --------------------------------------------------------
    # 4. Unknown / specific location
    # --------------------------------------------------------

    return location.strip()


def location_matches(
    job_location: str,
    preferred_locations: list[str],
) -> bool:
    """
    Determine whether a job location matches candidate preferences.

    Remote jobs are treated carefully:

        Remote - India        -> True
        Remote - United States -> False
        Remote - United Kingdom -> False
        Remote                 -> True

    Plain "Remote" is accepted because its country is unknown.
    """

    if not preferred_locations:
        return True

    normalized_job = normalize_location(
        job_location
    )

    # --------------------------------------------------------
    # Remote jobs
    # --------------------------------------------------------

    if normalized_job == "Remote":

        raw_job = _clean(job_location)

        # Explicit India remote
        if _contains_india(raw_job):
            return True

        # Explicit foreign remote
        if _contains_us(raw_job):
            return False

        # Detect explicit non-India remote locations.
        #
        # These are examples we can identify without needing
        # a complete country database.
        foreign_remote_markers = [
            "united kingdom",
            "uk",
            "england",
            "scotland",
            "wales",
            "ireland",
            "poland",
            "germany",
            "france",
            "canada",
            "australia",
            "singapore",
            "netherlands",
            "spain",
            "portugal",
            "italy",
            "israel",
            "japan",
            "south korea",
        ]

        if any(
            marker in raw_job
            for marker in foreign_remote_markers
        ):
            return False

        # Plain "Remote" with no country.
        return True

    # --------------------------------------------------------
    # Non-remote jobs
    # --------------------------------------------------------

    normalized_preferences = {
        normalize_location(preference)
        for preference in preferred_locations
    }

    # Exact normalized match
    if normalized_job in normalized_preferences:
        return True

    # Specific city/location fallback
    raw_job = _clean(job_location)

    for preferred in preferred_locations:

        normalized_preference = _clean(
            preferred
        )

        if not normalized_preference:
            continue

        # Don't use generic "remote" as a substring.
        if normalized_preference == "remote":
            continue

        if normalized_preference in raw_job:
            return True

    return False
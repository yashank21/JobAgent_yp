"""
Location normalization utilities.

Converts raw job-location strings into normalized
location categories used by the eligibility system.
"""

import re


INDIA_MARKERS = {
    "india",

    # Major cities
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
    "surat",
    "vadodara",
    "vapi",
    "indore",
    "bhopal",
    "jaipur",
    "lucknow",
    "chandigarh",
    "kochi",
    "thiruvananthapuram",
    "bhubaneswar",
    "nagpur",
    "patna",
    "visakhapatnam",
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

    Rules:

        India preference
            -> any recognized Indian physical location

        Specific city preference
            -> that city/location only

        Remote
            -> accepted when country is unknown or India
            -> rejected when explicitly foreign

    Examples:

        Vapi + ["India"]
            -> True

        Vapi + ["Pune"]
            -> False

        Pune + ["Pune"]
            -> True

        New Delhi + ["India"]
            -> True

        New Delhi + ["Bengaluru"]
            -> False
    """

    if not preferred_locations:
        return True

    normalized_job = normalize_location(
        job_location
    )

    raw_job = _clean(
        job_location
    )

    # --------------------------------------------------------
    # Remote jobs
    # --------------------------------------------------------

    if normalized_job == "Remote":

        # Explicit India remote
        if _contains_india(raw_job):
            return True

        # Explicit US remote
        if _contains_us(raw_job):
            return False

        # Explicit foreign remote
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

        # Plain "Remote" is accepted.
        return True

    # --------------------------------------------------------
    # Non-remote jobs
    # --------------------------------------------------------

    for preferred in preferred_locations:

        preferred_raw = _clean(
            preferred
        )

        if not preferred_raw:
            continue

        # ----------------------------------------------------
        # India-wide preference
        # ----------------------------------------------------

        if preferred_raw in {
            "india",
            "india only",
        }:

            if _contains_india(raw_job):
                return True

            continue

        # ----------------------------------------------------
        # United States-wide preference
        # ----------------------------------------------------

        if preferred_raw in {
            "united states",
            "usa",
            "us",
        }:

            if _contains_us(raw_job):
                return True

            continue

        # ----------------------------------------------------
        # India-wide preference
        # ----------------------------------------------------

        if preferred_raw in {
            "india",
            "india only",
        }:

            if _contains_india(
                raw_job
            ):
                return True

            continue

        # ----------------------------------------------------
        # Remote preference
        # ----------------------------------------------------

        if preferred_raw == "remote":

            # A physical job is not a remote job.
            continue

        # ----------------------------------------------------
        # Specific location preference
        # ----------------------------------------------------

        normalized_preference = normalize_location(
            preferred_raw
        )

        # IMPORTANT:
        #
        # Do NOT compare normalized values here.
        #
        # Pune and Vapi both normalize to "India".
        # That does NOT mean Pune == Vapi.
        #
        # Compare the raw/specific location instead.
        #

        if (
            preferred_raw == raw_job
        ):
            return True

        # Handle common variations.
        if (
            preferred_raw == "bengaluru"
            and raw_job == "bangalore"
        ):
            return True

        if (
            preferred_raw == "bangalore"
            and raw_job == "bengaluru"
        ):
            return True

        if (
            preferred_raw == "gurugram"
            and raw_job == "gurgaon"
        ):
            return True

        if (
            preferred_raw == "gurgaon"
            and raw_job == "gurugram"
        ):
            return True

        # Handle locations such as:
        #
        # "Pune, India"
        # "Bengaluru, India"
        # "New Delhi, India"
        #

        if re.search(
            rf"\b{re.escape(preferred_raw)}\b",
            raw_job,
        ):
            return True

    return False
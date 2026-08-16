import re
from enum import Enum


class RoleFamily(str, Enum):
    SOFTWARE_ENGINEERING = "software_engineering"
    MACHINE_LEARNING = "machine_learning"
    DATA_ENGINEERING = "data_engineering"
    BACKEND_ENGINEERING = "backend_engineering"
    FRONTEND_ENGINEERING = "frontend_engineering"
    DEVOPS = "devops"
    UNKNOWN = "unknown"


# More specific patterns must come before generic ones.
ROLE_PATTERNS = {
    RoleFamily.MACHINE_LEARNING: [
        r"\bmachine learning\b",
        r"\bml engineer\b",
        r"\bml engineering\b",
        r"\bai/ml\b",
        r"\bai engineer\b",
        r"\bapplied ml\b",
        r"\bdeep learning\b",
    ],

    RoleFamily.DATA_ENGINEERING: [
        r"\bdata engineer\b",
        r"\bdata engineering\b",
        r"\bbig data\b",
        r"\bdata platform\b",
        r"\banalytics engineer\b",
    ],

    RoleFamily.BACKEND_ENGINEERING: [
        r"\bbackend\b",
        r"\bback-end\b",
        r"\bserver-side\b",
    ],

    RoleFamily.FRONTEND_ENGINEERING: [
        r"\bfrontend\b",
        r"\bfront-end\b",
        r"\bui engineer\b",
        r"\bweb engineer\b",
    ],

    RoleFamily.DEVOPS: [
        r"\bdevops\b",
        r"\bdev ops\b",
        r"\bsite reliability\b",
        r"\bsre\b",
        r"\bplatform engineer\b",
        r"\binfrastructure engineer\b",
    ],

    RoleFamily.SOFTWARE_ENGINEERING: [
        r"\bsoftware engineer\b",
        r"\bsoftware engineering\b",
        r"\bsoftware developer\b",
        r"\bsoftware development\b",
        r"\bsoftware\b",
        r"\bsde\b",
        r"\bdevelopment engineer\b",
        r"\bnew graduate engineer\b",
    ],
}


def normalize_role_title(title: str) -> str:
    """
    Normalize a raw job title for role classification.
    """

    if not title:
        return ""

    title = title.lower().strip()

    # Remove academic/graduation year ranges BEFORE
    # replacing separators.
    #
    # Handles:
    # '26/'27
    # '26/27
    # 26/'27
    # 26/27
    # 2026/2027
    title = re.sub(
        r"'?\d{2,4}\s*/\s*'?\d{2,4}",
        " ",
        title,
    )

    # Remove standalone graduation years.
    title = re.sub(
        r"\b(?:19|20)\d{2}\b",
        " ",
        title,
    )

    # Normalize separators.
    title = re.sub(r"[-_/]", " ", title)

    # Remove excessive whitespace.
    title = re.sub(r"\s+", " ", title)

    return title.strip()


def classify_role(title: str) -> RoleFamily:
    """
    Classify a job title into its most likely role family.
    """

    normalized = normalize_role_title(title)

    if not normalized:
        return RoleFamily.UNKNOWN

    for family, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return family

    return RoleFamily.UNKNOWN
import re
from enum import Enum


class RoleFamily(str, Enum):
    AI_ENGINEERING = "ai_engineering"
    MACHINE_LEARNING = "machine_learning"
    LLM_GENAI = "llm_genai"
    FORWARD_DEPLOYED = "forward_deployed"

    DATA_SCIENCE = "data_science"
    DATA_ENGINEERING = "data_engineering"

    DEVOPS_ML_PLATFORM = "devops_ml_platform"
    DEVOPS = "devops"

    SOFTWARE_ENGINEERING = "software_engineering"
    BACKEND_ENGINEERING = "backend_engineering"
    FRONTEND_ENGINEERING = "frontend_engineering"

    # NEW
    RESEARCH_ENGINEERING = "research_engineering"
    MOBILE_ENGINEERING = "mobile_engineering"

    # NEW — intentionally not candidate-compatible
    SUPPORT_ENGINEERING = "support_engineering"
    CUSTOMER_ENGINEERING = "customer_engineering"
    INTEGRATION_ENGINEERING = "integration_engineering"
    RPA_ENGINEERING = "rpa_engineering"

    MANAGEMENT = "management"
    PRODUCT = "product"

    UNKNOWN = "unknown"


# ------------------------------------------------------------
# ROLE PATTERNS
# ------------------------------------------------------------
#
# IMPORTANT:
# More specific AI/ML families must come BEFORE generic
# software/backend/platform patterns.
#
# Example:
#
# "Software Engineer, Generative AI"
#       -> LLM_GENAI
#
# NOT:
#
#       -> SOFTWARE_ENGINEERING
#
# ------------------------------------------------------------

ROLE_PATTERNS = {

    # ========================================================
    # LLM / GENERATIVE AI
    # ========================================================

    RoleFamily.LLM_GENAI: [
        r"\bllm engineer\b",
        r"\bllm engineering\b",
        r"\blarge language model engineer\b",
        r"\bgenerative ai engineer\b",
        r"\bgenerative ai engineering\b",
        r"\bgenai engineer\b",
        r"\bgen ai engineer\b",
        r"\brag engineer\b",
        r"\bretrieval augmented generation engineer\b",
        r"\bretrieval augmented generation\b",
        r"\bprompt engineer\b",

        # Software Engineer + GenAI
        r"\bsoftware engineer.*generative ai\b",
        r"\bsoftware engineer.*genai\b",
        r"\bsoftware engineer.*gen ai\b",
        r"\bsoftware engineer.*llm\b",
    ],

    # ========================================================
    # DATA SCIENCE
    # ========================================================

    RoleFamily.DATA_SCIENCE: [
        r"\bmachine learning scientist\b",
        r"\bml scientist\b",
        r"\bdata scientist\b",
        r"\bdata science\b",
        r"\bapplied scientist\b",
        r"\bdata science engineer\b",
    ],

    # ========================================================
    # MACHINE LEARNING
    # ========================================================

    RoleFamily.MACHINE_LEARNING: [
        r"\bmachine learning engineer\b",
        r"\bmachine learning engineering\b",
        r"\bml engineer\b",
        r"\bml engineering\b",
        r"\bmle\b",
        r"\bai/ml engineer\b",
        r"\bai ml engineer\b",
        r"\bapplied ml engineer\b",
        r"\bapplied machine learning engineer\b",
        r"\bdeep learning engineer\b",

        # Software Engineer + ML
        r"\bsoftware engineer.*machine learning\b",
        r"\bsoftware engineer.*ml\b",
        r"\bsoftware engineer.*ai/ml\b",
        r"\bsoftware engineer.*ai ml\b",

        r"\bmachine learning\b",
        r"\bdeep learning\b",
    ],

    # ========================================================
    # AI ENGINEERING
    # ========================================================

    RoleFamily.AI_ENGINEERING: [
        r"\bai engineer\b",
        r"\bai engineering\b",
        r"\bartificial intelligence engineer\b",
        r"\bartificial intelligence engineering\b",
        r"\bapplied ai engineer\b",
        r"\bapplied artificial intelligence engineer\b",
        r"\bai applications engineer\b",
        r"\bai application engineer\b",
        r"\bai software engineer\b",

        # Software Engineer + AI
        r"\bsoftware engineer.*artificial intelligence\b",
        r"\bsoftware engineer.*\bai\b",
    ],

    # ========================================================
    # FORWARD DEPLOYED
    # ========================================================

    RoleFamily.FORWARD_DEPLOYED: [
        r"\bforward deployed engineer\b",
        r"\bforward-deployed engineer\b",
        r"\bforward deployed software engineer\b",
        r"\bforward-deployed software engineer\b",
        r"\bforward deployed ai engineer\b",
        r"\bforward-deployed ai engineer\b",
        r"\bforward deployed ml engineer\b",
        r"\bforward-deployed ml engineer\b",
    ],

    # ========================================================
    # DATA ENGINEERING
    # ========================================================

    RoleFamily.DATA_ENGINEERING: [
        r"\bdata engineer\b",
        r"\bdata engineering\b",
        r"\bbig data engineer\b",
        r"\bbig data\b",
        r"\bdata platform engineer\b",
        r"\bdata platform\b",
        r"\banalytics engineer\b",
        r"\banalytics engineering\b",
    ],

    # ========================================================
    # ML / AI PLATFORM
    # ========================================================

    RoleFamily.DEVOPS_ML_PLATFORM: [
        r"\bml platform engineer\b",
        r"\bmachine learning platform engineer\b",
        r"\bml infrastructure engineer\b",
        r"\bmachine learning infrastructure engineer\b",
        r"\bai platform engineer\b",
        r"\bai infrastructure engineer\b",
        r"\bmlops engineer\b",
        r"\bml ops engineer\b",
        r"\bmachine learning operations engineer\b",
    ],

    # ========================================================
    # BACKEND
    # ========================================================

    RoleFamily.BACKEND_ENGINEERING: [
        r"\bbackend engineer\b",
        r"\bbackend developer\b",
        r"\bback end engineer\b",
        r"\bback-end engineer\b",
        r"\bserver[- ]side engineer\b",

        # Backend + Software Engineer
        r"\bbackend software engineer\b",
        r"\bback end software engineer\b",
        r"\bback-end software engineer\b",
    ],

    # ========================================================
    # FRONTEND
    # ========================================================

    RoleFamily.FRONTEND_ENGINEERING: [
        r"\bfrontend engineer\b",
        r"\bfrontend developer\b",
        r"\bfront end engineer\b",
        r"\bfront-end engineer\b",
        r"\bui engineer\b",
        r"\bweb engineer\b",

        # Frontend + Software Engineer
        r"\bfrontend software engineer\b",
        r"\bfront end software engineer\b",
        r"\bfront-end software engineer\b",
    ],

    # ========================================================
    # DEVOPS
    # ========================================================

    RoleFamily.DEVOPS: [
        r"\bdevops engineer\b",
        r"\bdev ops engineer\b",
        r"\bsite reliability engineer\b",
        r"\bsre\b",
        r"\bplatform engineer\b",
        r"\binfrastructure engineer\b",
    ],

    # ========================================================
    # GENERIC SOFTWARE ENGINEERING
    # ========================================================

    RoleFamily.SOFTWARE_ENGINEERING: [
        r"\bsoftware engineer\b",
        r"\bsoftware engineering\b",
        r"\bsoftware developer\b",
        r"\bsoftware development engineer\b",
        r"\bsoftware development\b",
        r"\bsde\b",
        r"\bnew graduate engineer.*software\b",
    ],
    
    RoleFamily.SUPPORT_ENGINEERING: [
    r"\bsupport engineer\b",
    r"\btechnical support engineer\b",
    r"\bproduction support engineer\b",
    ],
    
    RoleFamily.CUSTOMER_ENGINEERING: [
    r"\bcustomer engineer\b",
    r"\bcustomer success engineer\b",
    r"\bsolutions engineer\b",
    r"\bfield engineer\b",
    ],
    
    RoleFamily.INTEGRATION_ENGINEERING: [
    r"\bintegration engineer\b",
    r"\bintegration developer\b",
    ],
    
    RoleFamily.INTEGRATION_ENGINEERING: [
    r"\bintegration engineer\b",
    r"\bintegration developer\b",
    ],
    
    RoleFamily.RPA_ENGINEERING: [
    r"\brpa engineer\b",
    r"\brpa developer\b",
    r"\brobotic process automation\b",
    ],
    
    RoleFamily.MANAGEMENT: [
    r"\bengineering manager\b",
    r"\bsoftware engineering manager\b",
    r"\bengineering director\b",
    r"\bhead of engineering\b",
    r"\bvp of engineering\b",
    ],
    
    RoleFamily.PRODUCT: [
    r"\bproduct manager\b",
    r"\bproduct management\b",
    ]
}


def normalize_role_title(title: str) -> str:
    """
    Normalize a raw job title for role classification.
    """

    if not title:
        return ""

    title = title.lower().strip()

    # --------------------------------------------------------
    # Remove academic / graduation year ranges BEFORE
    # replacing separators.
    #
    # Handles:
    # '26/'27
    # '26/27
    # 26/'27
    # 26/27
    # 2026/2027
    # --------------------------------------------------------

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

    title = re.sub(
        r"[-_/]",
        " ",
        title,
    )

    # Remove excessive whitespace.

    title = re.sub(
        r"\s+",
        " ",
        title,
    )

    return title.strip()


def classify_role(title: str) -> RoleFamily:
    """
    Classify a job title into its most likely role family.

    Pattern order is intentional:
    specialized AI/ML roles are evaluated before generic
    software/backend/platform roles.
    """

    normalized = normalize_role_title(title)

    if not normalized:
        return RoleFamily.UNKNOWN

    for family, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return family

    return RoleFamily.UNKNOWN
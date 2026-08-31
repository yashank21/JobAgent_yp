import re
from enum import Enum


class RoleFamily(str, Enum):
    # ========================================================
    # AI / ML
    # ========================================================

    AI_ENGINEERING = "ai_engineering"
    MACHINE_LEARNING = "machine_learning"
    LLM_GENAI = "llm_genai"
    FORWARD_DEPLOYED = "forward_deployed"

    # ========================================================
    # DATA
    # ========================================================

    DATA_SCIENCE = "data_science"
    DATA_ENGINEERING = "data_engineering"

    # ========================================================
    # PLATFORM / DEVOPS
    # ========================================================

    DEVOPS_ML_PLATFORM = "devops_ml_platform"
    DEVOPS = "devops"

    # ========================================================
    # SOFTWARE ENGINEERING
    # ========================================================

    SOFTWARE_ENGINEERING = "software_engineering"
    BACKEND_ENGINEERING = "backend_engineering"
    FRONTEND_ENGINEERING = "frontend_engineering"

    # ========================================================
    # SPECIALIZED ENGINEERING
    # ========================================================

    RESEARCH_ENGINEERING = "research_engineering"
    MOBILE_ENGINEERING = "mobile_engineering"

    SUPPORT_ENGINEERING = "support_engineering"
    CUSTOMER_ENGINEERING = "customer_engineering"
    INTEGRATION_ENGINEERING = "integration_engineering"
    RPA_ENGINEERING = "rpa_engineering"

    # ========================================================
    # NON-ENGINEERING / MANAGEMENT
    # ========================================================

    MANAGEMENT = "management"
    PRODUCT = "product"

    UNKNOWN = "unknown"


class SeniorityLevel(str, Enum):
    ENTRY = "entry"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    STAFF = "staff"
    PRINCIPAL = "principal"
    MANAGER = "manager"
    DIRECTOR = "director"
    UNKNOWN = "unknown"


# ============================================================
# ROLE PATTERNS
# ============================================================
#
# IMPORTANT:
#
# Specific roles MUST appear before generic roles.
#
# Example:
#
#   "Software Engineer, Generative AI"
#       -> LLM_GENAI
#
# NOT:
#
#   -> SOFTWARE_ENGINEERING
#
# Similarly:
#
#   "Engineering Manager"
#       -> MANAGEMENT
#
# NOT:
#
#   -> SOFTWARE_ENGINEERING
#
# ============================================================

ROLE_PATTERNS = {

    # ========================================================
    # MANAGEMENT
    # ========================================================

    RoleFamily.MANAGEMENT: [
    r"\bengineering manager\b",
    r"\bsoftware engineering manager\b",
    r"\bsoftware development manager\b",

    # Manager + Engineering
    r"\bmanager.*software engineering\b",
    r"\bmanager.*engineering\b",
    r"\bmanager.*software development\b",

    r"\btechnical manager\b",
    r"\bengineering director\b",
    r"\bsoftware engineering director\b",
    r"\bdirector of engineering\b",
    r"\bdirector of software engineering\b",
    r"\bhead of engineering\b",
    r"\bhead of software\b",
    r"\bvp of engineering\b",
    r"\bvice president of engineering\b",
    r"\bengineering lead\b",
],
    # ========================================================
    # PRODUCT
    # ========================================================

    RoleFamily.PRODUCT: [
        r"\bproduct manager\b",
        r"\bproduct management\b",
        r"\bproduct owner\b",
        r"\bproduct designer\b",
        r"\bproduct design\b",
        r"\bproduct analyst\b",
        r"\bproduct strategist\b",
        r"\bproduct strategy\b",
    ],

    # ========================================================
    # SUPPORT ENGINEERING
    # ========================================================

    RoleFamily.SUPPORT_ENGINEERING: [
        r"\bsupport engineer\b",
        r"\btechnical support engineer\b",
        r"\bproduction support engineer\b",
        r"\bapplication support engineer\b",
        r"\bsoftware support engineer\b",
        r"\bsupport developer\b",
    ],

    # ========================================================
    # CUSTOMER ENGINEERING
    # ========================================================

    RoleFamily.CUSTOMER_ENGINEERING: [
        r"\bcustomer engineer\b",
        r"\bcustomer success engineer\b",
        r"\bcustomer solutions engineer\b",
        r"\bsolutions engineer\b",
        r"\bfield engineer\b",
        r"\bfield applications engineer\b",
    ],

    # ========================================================
    # INTEGRATION ENGINEERING
    # ========================================================

    RoleFamily.INTEGRATION_ENGINEERING: [
        r"\bintegration engineer\b",
        r"\bintegration developer\b",
        r"\bintegration software engineer\b",
        r"\bapi integration engineer\b",
    ],

    # ========================================================
    # RPA
    # ========================================================

    RoleFamily.RPA_ENGINEERING: [
        r"\brpa engineer\b",
        r"\brpa developer\b",
        r"\brpa software engineer\b",
        r"\brobotic process automation\b",
        r"\bautomation anywhere\b",
        r"\buipath developer\b",
        r"\buipath engineer\b",
    ],

    # ========================================================
    # MOBILE
    # ========================================================

    RoleFamily.MOBILE_ENGINEERING: [
        r"\bmobile engineer\b",
        r"\bmobile developer\b",
        r"\bandroid engineer\b",
        r"\bandroid developer\b",
        r"\bios engineer\b",
        r"\bios developer\b",
        r"\bflutter developer\b",
        r"\breact native developer\b",
    ],

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
    # AI ENGINEERING
    #
    # Checked before MACHINE_LEARNING because "ai/ml engineer"
    # and "ai ml engineer" must classify as AI_ENGINEERING
    # (Wellfound slug: ai-engineer), not MACHINE_LEARNING.
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

        # ai/ml and ai ml variants — these are AI roles that
        # Wellfound resolves to the ai-engineer slug.
        r"\bai/ml\s+engineer\b",
        r"\bai\s+ml\s+engineer\b",

        # Software Engineer + AI
        r"\bsoftware engineer.*artificial intelligence\b",
        # Software Engineer + explicit AI specialization
        r"\bsoftware engineer\s*(?:,|-)\s*ai\b",
        r"\bsoftware engineer\s*(?:,|-)\s*artificial intelligence\b",
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
        r"\bapplied ml engineer\b",
        r"\bapplied machine learning engineer\b",
        r"\bdeep learning engineer\b",

        # Software Engineer + ML
        r"\bsoftware engineer.*machine learning\b",
        # Software Engineer + explicit ML specialization
        r"\bsoftware engineer\s*(?:,|-)\s*ml\b",
        r"\bsoftware engineer\s*(?:,|-)\s*machine learning\b",
        r"\bsoftware engineer.*ai/ml\b",
        r"\bsoftware engineer.*ai ml\b",

        r"\bmachine learning\b",
        r"\bdeep learning\b",
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
    # RESEARCH ENGINEERING
    # ========================================================

    RoleFamily.RESEARCH_ENGINEERING: [
        r"\bresearch engineer\b",
        r"\bresearch engineering\b",
        r"\bai research engineer\b",
        r"\bml research engineer\b",
        r"\bmachine learning research engineer\b",
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
}


# ============================================================
# SENIORITY PATTERNS
# ============================================================

SENIORITY_PATTERNS = {
    SeniorityLevel.DIRECTOR: [
        r"\bdirector\b",
        r"\bvice president\b",
        r"\bvp\b",
        r"\bhead of\b",
    ],

    SeniorityLevel.MANAGER: [
        r"\bengineering manager\b",
        r"\bsoftware engineering manager\b",
        r"\bengineering management\b",
        r"\bmanager\b",
    ],

    SeniorityLevel.PRINCIPAL: [
        r"\bprincipal\b",
    ],

    SeniorityLevel.STAFF: [
        r"\bstaff\b",
    ],

    SeniorityLevel.LEAD: [
        r"\blead\b",
        r"\btech lead\b",
        r"\btechnical lead\b",
    ],

    SeniorityLevel.SENIOR: [
        r"\bsenior\b",
        r"\bsr\b",
    ],

    SeniorityLevel.MID: [
        r"\bmid level\b",
        r"\bmid-level\b",
        r"\bexperienced\b",

        # Common engineering level conventions
        r"\bengineer ii\b",
        r"\bengineer iii\b",
        r"\bsde ii\b",
        r"\bsde iii\b",
        r"\blevel ii\b",
        r"\blevel iii\b",
        r"\blevel 2\b",
        r"\blevel 3\b",
    ],

    SeniorityLevel.ENTRY: [
        r"\bjunior\b",
        r"\bjr\b",
        r"\bentry level\b",
        r"\bgraduate\b",
        r"\bnew grad\b",
        r"\bnew graduate\b",
        r"\bearly career\b",
        r"\bengineer i\b",
        r"\bsde i\b",
        r"\blevel i\b",
        r"\blevel 1\b",
    ],
}


def normalize_role_title(title: str) -> str:
    """
    Normalize a raw job title for role classification.
    """

    if not title:
        return ""

    title = title.lower().strip()

    # --------------------------------------------------------
    # Remove academic / graduation year ranges.
    #
    # Handles:
    #   26/'27
    #   '26/'27
    #   26/27
    #   2026/2027
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


def classify_seniority(title: str) -> SeniorityLevel:
    """
    Classify job-title seniority.

    More senior levels are checked first.
    """

    normalized = normalize_role_title(title)

    if not normalized:
        return SeniorityLevel.UNKNOWN

    priority_order = [
        SeniorityLevel.DIRECTOR,
        SeniorityLevel.MANAGER,
        SeniorityLevel.PRINCIPAL,
        SeniorityLevel.STAFF,
        SeniorityLevel.LEAD,
        SeniorityLevel.SENIOR,
        SeniorityLevel.MID,
        SeniorityLevel.ENTRY,
    ]

    for level in priority_order:
        for pattern in SENIORITY_PATTERNS[level]:
            if re.search(pattern, normalized):
                return level

    return SeniorityLevel.UNKNOWN


def classify_role(title: str) -> RoleFamily:
    """
    Classify a job title into its most likely role family.

    Pattern order is intentional.

    Specialized and non-software roles are evaluated before
    generic software engineering.
    """

    normalized = normalize_role_title(title)

    if not normalized:
        return RoleFamily.UNKNOWN

    for family, patterns in ROLE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, normalized):
                return family

    return RoleFamily.UNKNOWN

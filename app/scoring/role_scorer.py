"""
Role scoring utilities.

Scores how well a job matches the candidate's target roles.

The scorer distinguishes between:

1. Primary roles
   - Core career targets.
   - Strongest role compatibility.

2. Secondary roles
   - Acceptable fallback/adjacent roles.
   - Intentionally scored lower than primary roles.

3. Seniority
   - Prevents senior/principal jobs from looking like
     excellent matches for an entry-level candidate.

Role family is more important than seniority, but severe
seniority mismatches are capped.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.scoring.role_normalizer import (
    RoleFamily,
    SeniorityLevel,
    classify_role,
    classify_seniority,
)


# ------------------------------------------------------------------
# Secondary role multiplier
# ------------------------------------------------------------------

SECONDARY_ROLE_MULTIPLIER = 0.75


# ------------------------------------------------------------------
# ROLE COMPATIBILITY
# ------------------------------------------------------------------
#
# Rows    = candidate preferred role
# Columns = actual job role
#
# These scores describe ROLE similarity only.
# Seniority is handled separately.
# ------------------------------------------------------------------

ROLE_COMPATIBILITY = {

    # ============================================================== 
    # AI ENGINEERING
    # ==============================================================

    RoleFamily.AI_ENGINEERING: {
        RoleFamily.AI_ENGINEERING: 100.0,
        RoleFamily.MACHINE_LEARNING: 95.0,
        RoleFamily.LLM_GENAI: 95.0,
        RoleFamily.RESEARCH_ENGINEERING: 90.0,
        RoleFamily.FORWARD_DEPLOYED: 85.0,
        RoleFamily.DATA_SCIENCE: 75.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 70.0,
        RoleFamily.DATA_ENGINEERING: 60.0,
        RoleFamily.BACKEND_ENGINEERING: 55.0,
        RoleFamily.SOFTWARE_ENGINEERING: 45.0,
    },

    # ============================================================== 
    # MACHINE LEARNING
    # ==============================================================

    RoleFamily.MACHINE_LEARNING: {
        RoleFamily.MACHINE_LEARNING: 100.0,
        RoleFamily.AI_ENGINEERING: 95.0,
        RoleFamily.LLM_GENAI: 95.0,
        RoleFamily.RESEARCH_ENGINEERING: 90.0,
        RoleFamily.DATA_SCIENCE: 85.0,
        RoleFamily.FORWARD_DEPLOYED: 80.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 75.0,
        RoleFamily.DATA_ENGINEERING: 65.0,
        RoleFamily.BACKEND_ENGINEERING: 55.0,
        RoleFamily.SOFTWARE_ENGINEERING: 45.0,
    },

    # ============================================================== 
    # LLM / GENAI
    # ==============================================================

    RoleFamily.LLM_GENAI: {
        RoleFamily.LLM_GENAI: 100.0,
        RoleFamily.AI_ENGINEERING: 95.0,
        RoleFamily.MACHINE_LEARNING: 95.0,
        RoleFamily.RESEARCH_ENGINEERING: 90.0,
        RoleFamily.FORWARD_DEPLOYED: 85.0,
        RoleFamily.DATA_SCIENCE: 75.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 70.0,
        RoleFamily.BACKEND_ENGINEERING: 60.0,
        RoleFamily.DATA_ENGINEERING: 60.0,
        RoleFamily.SOFTWARE_ENGINEERING: 50.0,
    },

    # ============================================================== 
    # RESEARCH ENGINEERING
    # ==============================================================

    RoleFamily.RESEARCH_ENGINEERING: {
        RoleFamily.RESEARCH_ENGINEERING: 100.0,
        RoleFamily.MACHINE_LEARNING: 95.0,
        RoleFamily.AI_ENGINEERING: 95.0,
        RoleFamily.LLM_GENAI: 95.0,
        RoleFamily.DATA_SCIENCE: 85.0,
        RoleFamily.FORWARD_DEPLOYED: 75.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 65.0,
        RoleFamily.DATA_ENGINEERING: 55.0,
        RoleFamily.BACKEND_ENGINEERING: 50.0,
        RoleFamily.SOFTWARE_ENGINEERING: 45.0,
    },

    # ============================================================== 
    # FORWARD DEPLOYED
    # ==============================================================

    RoleFamily.FORWARD_DEPLOYED: {
        RoleFamily.FORWARD_DEPLOYED: 100.0,
        RoleFamily.AI_ENGINEERING: 90.0,
        RoleFamily.MACHINE_LEARNING: 85.0,
        RoleFamily.LLM_GENAI: 85.0,
        RoleFamily.RESEARCH_ENGINEERING: 80.0,
        RoleFamily.DATA_SCIENCE: 75.0,
        RoleFamily.BACKEND_ENGINEERING: 65.0,
        RoleFamily.DATA_ENGINEERING: 60.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 60.0,
        RoleFamily.SOFTWARE_ENGINEERING: 55.0,
    },

    # ============================================================== 
    # DATA SCIENCE
    # ==============================================================

    RoleFamily.DATA_SCIENCE: {
        RoleFamily.DATA_SCIENCE: 100.0,
        RoleFamily.MACHINE_LEARNING: 90.0,
        RoleFamily.AI_ENGINEERING: 85.0,
        RoleFamily.LLM_GENAI: 80.0,
        RoleFamily.RESEARCH_ENGINEERING: 80.0,
        RoleFamily.DATA_ENGINEERING: 75.0,
        RoleFamily.FORWARD_DEPLOYED: 70.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 55.0,
        RoleFamily.BACKEND_ENGINEERING: 45.0,
        RoleFamily.SOFTWARE_ENGINEERING: 40.0,
    },

    # ============================================================== 
    # ML PLATFORM
    # ==============================================================

    RoleFamily.DEVOPS_ML_PLATFORM: {
        RoleFamily.DEVOPS_ML_PLATFORM: 100.0,
        RoleFamily.MACHINE_LEARNING: 80.0,
        RoleFamily.AI_ENGINEERING: 75.0,
        RoleFamily.LLM_GENAI: 70.0,
        RoleFamily.DATA_ENGINEERING: 70.0,
        RoleFamily.FORWARD_DEPLOYED: 65.0,
        RoleFamily.BACKEND_ENGINEERING: 65.0,
        RoleFamily.SOFTWARE_ENGINEERING: 55.0,
    },

    # ============================================================== 
    # DATA ENGINEERING
    # ==============================================================

    RoleFamily.DATA_ENGINEERING: {
        RoleFamily.DATA_ENGINEERING: 100.0,
        RoleFamily.DATA_SCIENCE: 85.0,
        RoleFamily.MACHINE_LEARNING: 75.0,
        RoleFamily.AI_ENGINEERING: 70.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 70.0,
        RoleFamily.LLM_GENAI: 65.0,
        RoleFamily.FORWARD_DEPLOYED: 60.0,
        RoleFamily.BACKEND_ENGINEERING: 60.0,
        RoleFamily.SOFTWARE_ENGINEERING: 0.0,
    },

    # ============================================================== 
    # BACKEND
    # ==============================================================

    RoleFamily.BACKEND_ENGINEERING: {
        RoleFamily.BACKEND_ENGINEERING: 100.0,
        RoleFamily.SOFTWARE_ENGINEERING: 90.0,
        RoleFamily.FORWARD_DEPLOYED: 70.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 65.0,
        RoleFamily.DATA_ENGINEERING: 60.0,
        RoleFamily.AI_ENGINEERING: 50.0,
        RoleFamily.MACHINE_LEARNING: 50.0,
        RoleFamily.LLM_GENAI: 50.0,
        RoleFamily.DATA_SCIENCE: 45.0,
    },

    # ============================================================== 
    # SOFTWARE ENGINEERING
    # ==============================================================

    RoleFamily.SOFTWARE_ENGINEERING: {
        RoleFamily.SOFTWARE_ENGINEERING: 100.0,
        RoleFamily.BACKEND_ENGINEERING: 90.0,
        RoleFamily.FORWARD_DEPLOYED: 65.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 60.0,
        RoleFamily.DATA_ENGINEERING: 55.0,
        RoleFamily.AI_ENGINEERING: 45.0,
        RoleFamily.MACHINE_LEARNING: 45.0,
        RoleFamily.LLM_GENAI: 45.0,
        RoleFamily.DATA_SCIENCE: 40.0,
    },
}


# ------------------------------------------------------------------
# SENIORITY COMPATIBILITY
# ------------------------------------------------------------------

SENIORITY_SCORES = {

    SeniorityLevel.ENTRY: {
        SeniorityLevel.ENTRY: 100.0,
        SeniorityLevel.MID: 80.0,
        SeniorityLevel.SENIOR: 55.0,
        SeniorityLevel.LEAD: 30.0,
        SeniorityLevel.STAFF: 15.0,
        SeniorityLevel.PRINCIPAL: 5.0,
        SeniorityLevel.MANAGER: 0.0,
        SeniorityLevel.DIRECTOR: 0.0,
    },

    SeniorityLevel.MID: {
        SeniorityLevel.ENTRY: 90.0,
        SeniorityLevel.MID: 100.0,
        SeniorityLevel.SENIOR: 85.0,
        SeniorityLevel.LEAD: 65.0,
        SeniorityLevel.STAFF: 50.0,
        SeniorityLevel.PRINCIPAL: 30.0,
        SeniorityLevel.MANAGER: 20.0,
        SeniorityLevel.DIRECTOR: 5.0,
    },

    SeniorityLevel.SENIOR: {
        SeniorityLevel.ENTRY: 70.0,
        SeniorityLevel.MID: 85.0,
        SeniorityLevel.SENIOR: 100.0,
        SeniorityLevel.LEAD: 85.0,
        SeniorityLevel.STAFF: 70.0,
        SeniorityLevel.PRINCIPAL: 50.0,
        SeniorityLevel.MANAGER: 35.0,
        SeniorityLevel.DIRECTOR: 10.0,
    },
}


# ------------------------------------------------------------------
# Candidate seniority
# ------------------------------------------------------------------

def _candidate_seniority(
    candidate: CandidateProfile,
) -> SeniorityLevel:

    years = max(
        candidate.experience_years,
        0.0,
    )

    if years <= 1.5:
        return SeniorityLevel.ENTRY

    if years <= 3.0:
        return SeniorityLevel.MID

    return SeniorityLevel.SENIOR


# ------------------------------------------------------------------
# Seniority score
# ------------------------------------------------------------------

def _seniority_score(
    candidate: CandidateProfile,
    job_seniority: SeniorityLevel,
) -> float:

    candidate_seniority = _candidate_seniority(candidate)

    if job_seniority == SeniorityLevel.UNKNOWN:
        return 70.0

    return SENIORITY_SCORES.get(
        candidate_seniority,
        {},
    ).get(
        job_seniority,
        50.0,
    )


# ------------------------------------------------------------------
# Role family score
# ------------------------------------------------------------------

def _score_role_pair(
    preferred_family: RoleFamily,
    job_family: RoleFamily,
) -> float:

    if (
        preferred_family == RoleFamily.UNKNOWN
        or job_family == RoleFamily.UNKNOWN
    ):
        return 0.0

    return ROLE_COMPATIBILITY.get(
        preferred_family,
        {},
    ).get(
        job_family,
        0.0,
    )


# ------------------------------------------------------------------
# Excluded role families
# ------------------------------------------------------------------

EXCLUDED_ROLE_FAMILIES = {
    RoleFamily.MANAGEMENT,
    RoleFamily.PRODUCT,
    RoleFamily.SUPPORT_ENGINEERING,
    RoleFamily.CUSTOMER_ENGINEERING,
    RoleFamily.INTEGRATION_ENGINEERING,
    RoleFamily.RPA_ENGINEERING,
    RoleFamily.MOBILE_ENGINEERING,
    RoleFamily.FRONTEND_ENGINEERING,
}


# ------------------------------------------------------------------
# Main role score
# ------------------------------------------------------------------

def calculate_role_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate role compatibility using:

    1. Primary role families
    2. Secondary role families
    3. Seniority compatibility

    Primary roles are only allowed to match strongly related
    role families.

    Secondary roles are fallback matches and are always
    scored lower than primary roles.

    Returns a score from 0 to 100.
    """

    if not candidate.preferred_roles:
        return 0.0

    job_family = classify_role(job.title)
    job_seniority = classify_seniority(job.title)

    if job_family == RoleFamily.UNKNOWN:
        return 0.0

    # --------------------------------------------------------
    # Roles that should NEVER be considered target roles.
    # --------------------------------------------------------

    excluded_families = {
        RoleFamily.MANAGEMENT,
        RoleFamily.PRODUCT,
        RoleFamily.SUPPORT_ENGINEERING,
        RoleFamily.CUSTOMER_ENGINEERING,
        RoleFamily.INTEGRATION_ENGINEERING,
        RoleFamily.RPA_ENGINEERING,
        RoleFamily.MOBILE_ENGINEERING,
        RoleFamily.FRONTEND_ENGINEERING,
    }

    if job_family in excluded_families:
        return 0.0

    # --------------------------------------------------------
    # Primary role families
    # --------------------------------------------------------

    primary_families = {
        classify_role(role)
        for role in candidate.preferred_roles
    }

    primary_families.discard(RoleFamily.UNKNOWN)
    primary_families -= excluded_families

    # --------------------------------------------------------
    # Secondary role families
    # --------------------------------------------------------

    secondary_roles = getattr(
        candidate,
        "secondary_roles",
        [],
    )

    secondary_families = {
        classify_role(role)
        for role in secondary_roles
    }

    secondary_families.discard(RoleFamily.UNKNOWN)
    secondary_families -= excluded_families

    # --------------------------------------------------------
    # Seniority
    # --------------------------------------------------------

    seniority_score = _seniority_score(
        candidate,
        job_seniority,
    )

    # ========================================================
    # PRIMARY ROLE MATCH
    # ========================================================
    #
    # IMPORTANT:
    #
    # A primary role must have >= 70 role-family compatibility.
    #
    # This prevents things like:
    #
    # LLM Engineer -> Backend Engineer = 60
    #
    # from being incorrectly treated as a primary match.
    #
    # The candidate explicitly listed Backend Engineer as a
    # secondary role, so the backend job must fall through to
    # secondary scoring.
    # ========================================================

    PRIMARY_MATCH_THRESHOLD = 70.0

    best_primary_score = 0.0

    for preferred_family in primary_families:

        family_score = _score_role_pair(
            preferred_family,
            job_family,
        )

        if family_score < PRIMARY_MATCH_THRESHOLD:
            continue

        role_score = (
            family_score * 0.75
            + seniority_score * 0.25
        )

        # ----------------------------------------------------
        # Seniority mismatch caps
        # ----------------------------------------------------

        if seniority_score < 20:
            role_score = min(
                role_score,
                45.0,
            )

        elif seniority_score < 40:
            role_score = min(
                role_score,
                60.0,
            )

        elif seniority_score < 60:
            role_score = min(
                role_score,
                80.0,
            )

        best_primary_score = max(
            best_primary_score,
            role_score,
        )

        # ========================================================
    # SECONDARY ROLE MATCH
    # ========================================================
    #
    # Secondary roles are fallback roles.
    #
    # Even an exact secondary role should NOT compete with
    # an exact primary role.
    # ========================================================

    best_secondary_score = 0.0

    for secondary_family in secondary_families:

        family_score = _score_role_pair(
            secondary_family,
            job_family,
        )

        if family_score <= 0:
            continue

        role_score = (
            family_score * 0.70
            + seniority_score * 0.30
        )

        # Secondary roles receive a hard reduction.
        role_score *= 0.70

        # Secondary roles are fallback opportunities.
        role_score = min(
            role_score,
            60.0,
        )

        # Entry-level candidates should not receive
        # high scores for senior secondary-role jobs.
        if seniority_score < 60:
            role_score = min(
                role_score,
                50.0,
            )

        best_secondary_score = max(
            best_secondary_score,
            role_score,
        )

    # ========================================================
    # PRIMARY ALWAYS WINS
    # ========================================================

    if best_primary_score > 0:
        return round(
            best_primary_score,
            2,
        )

    if best_secondary_score > 0:
        return round(
            best_secondary_score,
            2,
        )

    return 0.0
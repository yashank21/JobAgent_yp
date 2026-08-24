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
        RoleFamily.DEVOPS: 55.0,
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
        RoleFamily.DEVOPS: 55.0,
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
        RoleFamily.DEVOPS: 50.0,
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
        RoleFamily.DEVOPS: 45.0,
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
        RoleFamily.DEVOPS: 90.0,
        RoleFamily.MACHINE_LEARNING: 80.0,
        RoleFamily.AI_ENGINEERING: 75.0,
        RoleFamily.LLM_GENAI: 70.0,
        RoleFamily.DATA_ENGINEERING: 70.0,
        RoleFamily.FORWARD_DEPLOYED: 65.0,
        RoleFamily.BACKEND_ENGINEERING: 65.0,
        RoleFamily.SOFTWARE_ENGINEERING: 55.0,
    },
    
    RoleFamily.DEVOPS: {
        RoleFamily.DEVOPS: 100.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 90.0,
        RoleFamily.BACKEND_ENGINEERING: 75.0,
        RoleFamily.DATA_ENGINEERING: 75.0,
        RoleFamily.SOFTWARE_ENGINEERING: 65.0,
        RoleFamily.MACHINE_LEARNING: 55.0,
        RoleFamily.AI_ENGINEERING: 50.0,
        RoleFamily.LLM_GENAI: 50.0,
        RoleFamily.DATA_SCIENCE: 45.0,
        RoleFamily.RESEARCH_ENGINEERING: 45.0,
        RoleFamily.FORWARD_DEPLOYED: 65.0,
    },

    # ============================================================== 
    # DATA ENGINEERING
    # ==============================================================

    RoleFamily.DATA_ENGINEERING: {
        RoleFamily.DATA_ENGINEERING: 100.0,
        RoleFamily.DATA_SCIENCE: 85.0,
        RoleFamily.MACHINE_LEARNING: 75.0,
        RoleFamily.AI_ENGINEERING: 70.0,
        RoleFamily.DEVOPS: 75.0,
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
        RoleFamily.DEVOPS: 70.0,
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
        RoleFamily.DEVOPS: 60.0,
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

def _resolve_role_family(
    value: str | RoleFamily,
) -> RoleFamily:
    """
    Resolve either a RoleFamily value or a natural-language
    role/title into a RoleFamily.
    """

    if isinstance(value, RoleFamily):
        return value

    if not value:
        return RoleFamily.UNKNOWN

    normalized = str(value).strip().lower()

    # Direct canonical RoleFamily value.
    for family in RoleFamily:
        if normalized == family.value:
            return family

    # Otherwise treat it as a natural-language title.
    return classify_role(str(value))


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
    scdef calculate_role_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    if not candidate.preferred_roles:
        return 0.0

    # --------------------------------------------------------
    # Determine job role family
    # --------------------------------------------------------

    gemini_role_family = getattr(
        job,
        "role_family",
        "",
    )

    gemini_confidence = float(
        getattr(
            job,
            "gemini_confidence",
            0.0,
        )
        or 0.0
    )

    if (
        gemini_role_family
        and str(gemini_role_family).lower() != "other"
        and gemini_confidence >= 0.60
    ):
        job_family = _resolve_role_family(
            gemini_role_family
        )
    else:
        job_family = classify_role(
            job.title
        )

    # --------------------------------------------------------
    # Determine job seniority
    # --------------------------------------------------------

    gemini_seniority = getattr(
        job,
        "seniority",
        "",
    )

    if (
        gemini_seniority
        and gemini_seniority.lower() != "unknown"
        and gemini_confidence >= 0.60
    ):
        try:
            job_seniority = classify_seniority(
                gemini_seniority
            )
        except Exception:
            job_seniority = classify_seniority(
                job.title
            )
    else:
        job_seniority = classify_seniority(
            job.title
        )

    if job_family == RoleFamily.UNKNOWN:
        return 0.0

    # --------------------------------------------------------
    # Roles that should never be target roles
    # --------------------------------------------------------

    if job_family in EXCLUDED_ROLE_FAMILIES:
        return 0.0

    # --------------------------------------------------------
    # Primary role families
    # --------------------------------------------------------

    primary_families = {
        classify_role(role)
        for role in candidate.preferred_roles
    }

    primary_families.discard(RoleFamily.UNKNOWN)
    primary_families -= EXCLUDED_ROLE_FAMILIES

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
    secondary_families -= EXCLUDED_ROLE_FAMILIES

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

    best_primary_score = 0.0

    for preferred_family in primary_families:

        family_score = _score_role_pair(
            preferred_family,
            job_family,
        )

        if family_score <= 0:
            continue

        role_score = family_score

        # ----------------------------------------------------
        # Seniority is NOT blended into normal role similarity.
        #
        # A Software Engineer is still a Software Engineer
        # even if the job is slightly more senior.
        # ----------------------------------------------------

        if seniority_score < 20:
            role_score = min(role_score, 60.0)

        elif seniority_score < 40:
            role_score = min(role_score, 75.0)

        elif seniority_score < 60:
            role_score = min(role_score, 85.0)

        best_primary_score = max(
            best_primary_score,
            role_score,
        )

    # ========================================================
    # SECONDARY ROLE MATCH
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
            family_score
            * SECONDARY_ROLE_MULTIPLIER
        )

        # Secondary roles are intentionally weaker.
        role_score = min(
            role_score,
            70.0,
        )

        if seniority_score < 40:
            role_score = min(
                role_score,
                55.0,
            )

        best_secondary_score = max(
            best_secondary_score,
            role_score,
        )

        # ========================================================
        # FINAL ROLE SCORE
        # ========================================================

        return round(
            max(
                best_primary_score,
                best_secondary_score,
            ),
            2,
        )
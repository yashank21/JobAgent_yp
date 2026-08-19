"""
Role scoring utilities.

Scores how well a job title matches the candidate's preferred
role families.

Unlike eligibility, role scoring is not binary. A job can be
highly relevant, somewhat relevant, or weakly relevant to the
candidate's preferred role.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
)


# ------------------------------------------------------------------
# Role compatibility
# ------------------------------------------------------------------
#
# Rows = candidate's preferred role
# Columns = actual job role.
#
# Scores represent how strongly the job role aligns with the
# candidate's preferred role.
#
# 100 = essentially the same role
#  90 = extremely strong adjacent role
#  75 = strong adjacent role
#  60 = reasonable adjacent role
#  40 = weak but potentially useful
#   0 = unrelated
# ------------------------------------------------------------------

ROLE_COMPATIBILITY = {

    RoleFamily.AI_ENGINEERING: {
        RoleFamily.AI_ENGINEERING: 100.0,
        RoleFamily.MACHINE_LEARNING: 95.0,
        RoleFamily.LLM_GENAI: 95.0,
        RoleFamily.FORWARD_DEPLOYED: 85.0,
        RoleFamily.DATA_SCIENCE: 75.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 70.0,
        RoleFamily.DATA_ENGINEERING: 60.0,
        RoleFamily.BACKEND_ENGINEERING: 50.0,
        RoleFamily.SOFTWARE_ENGINEERING: 40.0,
    },

    RoleFamily.MACHINE_LEARNING: {
        RoleFamily.MACHINE_LEARNING: 100.0,
        RoleFamily.AI_ENGINEERING: 95.0,
        RoleFamily.LLM_GENAI: 95.0,
        RoleFamily.DATA_SCIENCE: 85.0,
        RoleFamily.FORWARD_DEPLOYED: 80.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 75.0,
        RoleFamily.DATA_ENGINEERING: 65.0,
        RoleFamily.BACKEND_ENGINEERING: 50.0,
        RoleFamily.SOFTWARE_ENGINEERING: 40.0,
    },

    RoleFamily.LLM_GENAI: {
        RoleFamily.LLM_GENAI: 100.0,
        RoleFamily.AI_ENGINEERING: 95.0,
        RoleFamily.MACHINE_LEARNING: 95.0,
        RoleFamily.FORWARD_DEPLOYED: 85.0,
        RoleFamily.DATA_SCIENCE: 75.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 70.0,
        RoleFamily.DATA_ENGINEERING: 60.0,
        RoleFamily.BACKEND_ENGINEERING: 50.0,
        RoleFamily.SOFTWARE_ENGINEERING: 40.0,
    },

    RoleFamily.FORWARD_DEPLOYED: {
        RoleFamily.FORWARD_DEPLOYED: 100.0,
        RoleFamily.AI_ENGINEERING: 90.0,
        RoleFamily.MACHINE_LEARNING: 85.0,
        RoleFamily.LLM_GENAI: 85.0,
        RoleFamily.DATA_SCIENCE: 75.0,
        RoleFamily.BACKEND_ENGINEERING: 65.0,
        RoleFamily.DATA_ENGINEERING: 60.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 60.0,
        RoleFamily.SOFTWARE_ENGINEERING: 55.0,
    },

    RoleFamily.DATA_SCIENCE: {
        RoleFamily.DATA_SCIENCE: 100.0,
        RoleFamily.MACHINE_LEARNING: 90.0,
        RoleFamily.AI_ENGINEERING: 85.0,
        RoleFamily.LLM_GENAI: 80.0,
        RoleFamily.DATA_ENGINEERING: 75.0,
        RoleFamily.FORWARD_DEPLOYED: 70.0,
        RoleFamily.DEVOPS_ML_PLATFORM: 55.0,
        RoleFamily.BACKEND_ENGINEERING: 45.0,
        RoleFamily.SOFTWARE_ENGINEERING: 40.0,
    },

    RoleFamily.DEVOPS_ML_PLATFORM: {
        RoleFamily.DEVOPS_ML_PLATFORM: 100.0,
        RoleFamily.MACHINE_LEARNING: 80.0,
        RoleFamily.AI_ENGINEERING: 75.0,
        RoleFamily.LLM_GENAI: 70.0,
        RoleFamily.FORWARD_DEPLOYED: 65.0,
        RoleFamily.DATA_ENGINEERING: 70.0,
        RoleFamily.BACKEND_ENGINEERING: 65.0,
        RoleFamily.SOFTWARE_ENGINEERING: 55.0,
    },

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


def _score_role_pair(
    preferred_family: RoleFamily,
    job_family: RoleFamily,
) -> float:
    """
    Return compatibility score between two role families.
    """

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


def calculate_role_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate how well the job title matches the candidate's
    preferred roles.

    Returns a score from 0.0 to 100.0.

    If the candidate has multiple preferred roles, the strongest
    compatibility score is used.
    """

    if not candidate.preferred_roles:
        return 0.0

    job_family = classify_role(job.title)

    if job_family == RoleFamily.UNKNOWN:
        return 0.0

    best_score = 0.0

    for preferred_role in candidate.preferred_roles:

        preferred_family = classify_role(
            preferred_role
        )

        score = _score_role_pair(
            preferred_family,
            job_family,
        )

        best_score = max(
            best_score,
            score,
        )

    return best_score
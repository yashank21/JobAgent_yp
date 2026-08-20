"""
Job scoring utilities.

Scores how well a job matches a candidate profile.

Required skills are the primary signal.
Preferred skills provide additional refinement when present.
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.services.skill_normalizer import normalize_skills


REQUIRED_WEIGHT = 0.80
PREFERRED_WEIGHT = 0.20


def calculate_skill_score(
    candidate: CandidateProfile,
    job: Job,
) -> float:
    """
    Calculate skill alignment from 0 to 100.

    Rules:

    1. Required skills are the primary signal.
    2. Preferred skills provide additional signal when present.
    3. A job with no preferred skills is NOT penalized.
    4. A job with no skill requirements receives 0 because
       there is insufficient evidence to judge skill alignment.

    Examples:

        Required only:
            10/10 matched -> 100

        Required + preferred:
            10/10 required + 0/5 preferred
            -> 80

        Required + preferred:
            10/10 required + 5/5 preferred
            -> 100
    """

    candidate_skills = normalize_skills(
        candidate.skills
    )

    required_skills = normalize_skills(
        job.required_skills
    )

    preferred_skills = normalize_skills(
        job.preferred_skills
    )

    # --------------------------------------------------------
    # No skill information
    # --------------------------------------------------------

    if not required_skills and not preferred_skills:
        return 0.0

    # --------------------------------------------------------
    # Required skills
    # --------------------------------------------------------

    required_score = 0.0

    if required_skills:
        matched_required = (
            required_skills & candidate_skills
        )

        required_score = (
            len(matched_required)
            / len(required_skills)
        ) * 100.0

    # --------------------------------------------------------
    # Preferred skills
    # --------------------------------------------------------

    preferred_score = 0.0

    if preferred_skills:
        matched_preferred = (
            preferred_skills & candidate_skills
        )

        preferred_score = (
            len(matched_preferred)
            / len(preferred_skills)
        ) * 100.0

    # --------------------------------------------------------
    # Required skills only
    #
    # Do NOT artificially cap these jobs at 80%.
    # --------------------------------------------------------

    if required_skills and not preferred_skills:
        return round(
            required_score,
            2,
        )

    # --------------------------------------------------------
    # Preferred skills exist
    # --------------------------------------------------------

    if required_skills:
        score = (
            required_score * REQUIRED_WEIGHT
            + preferred_score * PREFERRED_WEIGHT
        )

    else:
        # Job has only preferred skills.
        score = preferred_score

    return round(
        score,
        2,
    )
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.job_scorer import calculate_skill_score
from app.scoring.experience_scorer import calculate_experience_score
from app.scoring.match_result import JobMatchResult


def calculate_match(
    candidate: CandidateProfile,
    job: Job,
) -> JobMatchResult:
    """
    Calculate the overall match between a candidate and a job.
    """

    skill_score = calculate_skill_score(
        candidate,
        job,
    )

    experience_score = calculate_experience_score(
        candidate,
        job,
    )

    overall_score = (
        skill_score * 0.7
        + experience_score * 0.3
    )

    reasons = []

    if skill_score >= 80:
        reasons.append(
            "Strong skill match"
        )
    elif skill_score >= 50:
        reasons.append(
            "Partial skill match"
        )
    else:
        reasons.append(
            "Weak skill match"
        )

    if experience_score >= 80:
        reasons.append(
            "Experience requirement is satisfied"
        )
    elif experience_score > 0:
        reasons.append(
            "Candidate has partial required experience"
        )
    else:
        reasons.append(
            "Experience requirement is not satisfied"
        )

    return JobMatchResult(
        overall_score=overall_score,
        skill_score=skill_score,
        experience_score=experience_score,
        reasons=reasons,
    )
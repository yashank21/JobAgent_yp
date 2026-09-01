from dataclasses import dataclass, field

from app.models.job import Job


@dataclass
class JobMatch:

    job: Job

    eligible: bool = True

    skill_score: float = 0.0
    role_score: float = 0.0
    experience_score: float = 0.0
    experience_risk: str = "unknown"
    location_score: float = 0.0
    salary_score: float = 0.0

    # Weighted average of active dimensions (Step 3 formula).
    compatibility_score: float = 0.0

    # Confidence in the compatibility calculation (0-1).
    # Based on availability of ranking-relevant job information.
    confidence: float = 1.0

    # Final ranking score = compatibility * confidence_factor.
    final_score: float = 0.0

    eligibility_reasons: list[str] = field(
        default_factory=list
    )

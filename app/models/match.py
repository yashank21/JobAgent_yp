from dataclasses import dataclass, field

from app.models.job import Job


@dataclass
class JobMatch:

    job: Job

    eligible: bool = True

    skill_score: float = 0.0
    role_score: float = 0.0
    experience_score: float = 0.0
    location_score: float = 0.0
    salary_score: float = 0.0

    final_score: float = 0.0

    eligibility_reasons: list[str] = field(
        default_factory=list
    )

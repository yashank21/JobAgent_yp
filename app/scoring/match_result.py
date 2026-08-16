from dataclasses import dataclass, field


@dataclass
class JobMatchResult:
    overall_score: float

    skill_score: float
    experience_score: float

    reasons: list[str] = field(default_factory=list)
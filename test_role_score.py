from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.role_scorer import calculate_role_score


jobs = [
    ("AI Engineer", "ai_engineering", "entry"),
    ("ML Engineer", "machine_learning", "entry"),
    ("LLM Engineer", "llm_genai", "entry"),
    ("Software Engineer", "software_engineering", "entry"),
    ("Backend Engineer", "backend_engineering", "entry"),
    ("Senior AI Engineer", "ai_engineering", "senior"),
    ("Staff Software Engineer", "software_engineering", "staff"),
    ("Data Engineer", "data_engineering", "entry"),
    ("DevOps Engineer", "devops", "entry"),
    ("Product Manager", "product", "manager"),
]


if __name__ == "__main__":
    candidate = CandidateProfile(
        preferred_roles=["AI Engineer"],
    )

    for title, role, seniority in jobs:
        job = Job(
            id="test",
            company="Test",
            title=title,
            role_family=role,
            seniority=seniority,
        )

        score = calculate_role_score(candidate, job)
        print(f"{title:<30} -> {score:.2f}")

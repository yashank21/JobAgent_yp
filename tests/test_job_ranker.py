from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.job_ranker import rank_jobs


def test_jobs_are_ranked_highest_first():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        skills=["Python", "C++"],
    )

    weak_job = Job(
        id="1",
        title="Software Engineer",
        company="Weak Corp",
        required_skills=["Java"],
    )

    strong_job = Job(
        id="2",
        title="Software Engineer",
        company="Strong Corp",
        required_skills=["Python", "C++"],
    )

    ranked = rank_jobs(
        candidate,
        [weak_job, strong_job],
    )

    assert ranked[0][0].company == "Strong Corp"
    assert ranked[1][0].company == "Weak Corp"

    assert ranked[0][1] > ranked[1][1]


def test_rank_jobs_limit():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        skills=["Python"],
    )

    jobs = [
        Job(
            id=str(i),
            title="Software Engineer",
            company=f"Company {i}",
            required_skills=["Python"],
        )
        for i in range(10)
    ]

    ranked = rank_jobs(
        candidate,
        jobs,
        limit=5,
    )

    assert len(ranked) == 5
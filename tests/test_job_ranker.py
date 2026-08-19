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

    assert ranked[0].job.company == "Strong Corp"
    assert ranked[1].job.company == "Weak Corp"

    assert ranked[0].final_score > ranked[1].final_score


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


def test_ineligible_jobs_are_not_ranked():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        preferred_roles=["Software Engineer"],
        preferred_locations=["India"],
        skills=["Python"],
    )

    eligible_job = Job(
        id="1",
        title="Software Engineer",
        company="Eligible Corp",
        location="Bengaluru, India",
        required_skills=["Python"],
    )

    ineligible_job = Job(
        id="2",
        title="Food Services Specialist",
        company="Ineligible Corp",
        location="Hawthorne, CA",
        required_skills=["Python"],
    )

    ranked = rank_jobs(
        candidate,
        [ineligible_job, eligible_job],
    )

    companies = [
        match.job.company
        for match in ranked
    ]

    assert "Eligible Corp" in companies
    assert "Ineligible Corp" not in companies


def test_role_mismatch_is_not_ranked():

    candidate = CandidateProfile(
        name="Yashank",
        email="test@example.com",
        location="India",
        preferred_roles=["Software Engineer"],
        preferred_locations=["India"],
        skills=["Python"],
    )

    wrong_role = Job(
        id="1",
        title="Production Control Scheduler",
        company="Wrong Role Corp",
        location="Bengaluru, India",
        required_skills=["Python"],
    )

    ranked = rank_jobs(
        candidate,
        [wrong_role],
    )

    assert ranked == []
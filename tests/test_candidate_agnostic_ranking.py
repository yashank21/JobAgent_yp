from datetime import datetime, timezone

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.final_scorer import rank_jobs, score_job


def _candidate(**kwargs):
    defaults = {
        "name": "Test User",
        "email": "user@example.com",
        "experience_years": 2.0,
        "career_level": "entry",
        "skills": ["Python", "SQL"],
        "preferred_locations": ["Remote"],
    }
    defaults.update(kwargs)
    return CandidateProfile(**defaults)


def _job(**kwargs):
    defaults = {
        "id": "job-1",
        "title": "Software Engineer",
        "company": "Acme",
        "location": "Remote",
        "remote_type": "Remote",
        "required_skills": ["Python"],
        "posted_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return Job(**defaults)


def test_ai_user_ranks_ai_job_above_frontend_job():
    candidate = _candidate(preferred_roles=["AI Engineer"])
    ranked = rank_jobs(
        candidate,
        [
            _job(id="fe", title="Frontend Engineer"),
            _job(id="ai", title="AI Engineer"),
        ],
    )
    ids = [match.job.id for match in ranked]
    assert "ai" in ids
    assert ids[0] == "ai"


def test_backend_user_ranks_backend_above_ai():
    candidate = _candidate(preferred_roles=["Backend Engineer"])
    ranked = rank_jobs(
        candidate,
        [
            _job(id="ai", title="AI Engineer"),
            _job(id="be", title="Backend Engineer"),
        ],
    )
    assert ranked[0].job.id == "be"


def test_same_jobs_rank_differently_for_different_users():
    jobs = [
        _job(id="ai", title="AI Engineer", required_skills=["Python"]),
        _job(id="fe", title="Frontend Engineer", required_skills=["Python"]),
    ]

    ai_ranked = rank_jobs(
        _candidate(preferred_roles=["AI Engineer"]),
        jobs,
    )
    fe_ranked = rank_jobs(
        _candidate(preferred_roles=["Frontend Engineer"]),
        jobs,
    )

    assert ai_ranked[0].job.id != fe_ranked[0].job.id
    assert ai_ranked[0].job.id == "ai"
    assert fe_ranked[0].job.id == "fe"


def test_primary_ai_role_beats_secondary_software_when_skills_unknown():
    """When skills are unknown (no listed skills), the job with
    the stronger role match should rank higher.

    Before Step 2 fix: missing skills were excluded from weighting,
    giving information-sparse jobs an unfair advantage.

    After Step 2 fix: missing skills return neutral 50.0 and always
    participate in scoring.  Role preference still matters, but
    skill match now participates in the final calculation.
    """
    candidate = _candidate(
        preferred_roles=["AI Engineer"],
        secondary_roles=["Software Engineer"],
        skills=["Python", "PyTorch"],
    )

    ranked = rank_jobs(
        candidate,
        [
            _job(
                id="swe",
                title="Software Engineer, Infrastructure",
                required_skills=["Python"],
            ),
            _job(
                id="ai",
                title="Applied AI Engineer",
                required_skills=[],
            ),
        ],
    )

    # SWE job has 100% skill match (Python matches) + secondary
    # role (85.0).  AI job has neutral skill (50.0) + primary
    # role (100.0).
    #
    # SWE: 100*0.40 + 85*0.30 + 100*0.20 + 100*0.10 = 95.5
    # AI:   50*0.40 + 100*0.30 + 100*0.20 + 100*0.10 = 90.0
    #
    # SWE ranks higher because skill match now participates.
    assert ranked[0].job.id == "swe"


def test_wrong_role_is_not_eligible_when_user_stated_intent():
    candidate = _candidate(preferred_roles=["Backend Engineer"])
    match = score_job(
        candidate,
        _job(title="Mechanical Engineer"),
    )
    assert match.eligible is False

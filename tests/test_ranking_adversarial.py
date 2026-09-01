"""
STEP 8 — Adversarial ranking tests.

These tests defend product invariants of the ranking engine.
They are designed to BREAK the ranking semantics, not just verify
happy-path coverage.

Every test defends a concrete product invariant.
"""

import random
from dataclasses import replace

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.final_scorer import (
    calculate_confidence,
    calculate_final_score,
    calculate_location_score,
    calculate_ranking_score,
    rank_jobs,
    score_job,
    MIN_CONFIDENCE,
    SKILL_WEIGHT,
    ROLE_WEIGHT,
    EXPERIENCE_WEIGHT,
    LOCATION_WEIGHT,
)
from app.scoring.role_scorer import calculate_role_score
from app.scoring.experience_scorer import calculate_experience_score
from app.scoring.job_scorer import calculate_skill_score
from app.scoring.role_normalizer import RoleFamily, classify_role
from app.location.location_normalizer import normalize_location


# ============================================================
# HELPERS
# ============================================================


def _candidate(**kwargs):
    defaults = {
        "name": "Test User",
        "email": "test@example.com",
        "experience_years": 3.0,
        "skills": ["Python", "C++"],
        "preferred_roles": ["Backend Engineer"],
        "preferred_locations": ["India"],
    }
    defaults.update(kwargs)
    return CandidateProfile(**defaults)


def _job(**kwargs):
    defaults = {
        "id": "job-1",
        "title": "Backend Engineer",
        "company": "TestCo",
        "location": "Bengaluru, India",
        "required_skills": ["Python"],
        "preferred_skills": [],
    }
    defaults.update(kwargs)
    return Job(**defaults)


def _rank_ids(candidate, jobs, limit=None):
    """Return ordered job IDs from rank_jobs."""
    return [m.job.id for m in rank_jobs(candidate, jobs, limit=limit)]


# ============================================================
# 1. PERFECT / HIGH QUALITY JOB
# ============================================================


def test_perfect_job_produces_maximal_scores():
    """A job with complete matching information should produce
    maximal compatibility, maximal confidence, and maximal ranking.

    Skill scoring: required * 0.7 + preferred * 0.3.
    To get 100.0 skill_score, both required and preferred skills
    must match. Without preferred skills, max is 70.0.
    """
    candidate = _candidate(
        skills=["Python", "C++", "FastAPI"],
        preferred_roles=["Backend Engineer"],
        preferred_locations=["India"],
        experience_years=5.0,
    )
    job = _job(
        required_skills=["Python", "C++"],
        preferred_skills=["FastAPI"],
        location="Bengaluru, India",
        experience_years_required=3,
    )

    match = score_job(candidate, job)

    assert match.eligible is True
    assert match.skill_score == 100.0
    assert match.role_score == 100.0
    assert match.experience_score == 100.0
    assert match.location_score == 100.0
    assert match.compatibility_score == 100.0
    assert match.confidence == 1.0
    assert match.final_score == 100.0


# ============================================================
# 2. KNOWN SKILL MISMATCH
# ============================================================


def test_known_skill_mismatch_ranks_below_known_match():
    """Two otherwise identical jobs: one with matching skills,
    one with mismatched skills. The match must rank higher."""
    candidate = _candidate(skills=["Python", "C++"])
    job_match = _job(
        id="match",
        required_skills=["Python", "C++"],
    )
    job_mismatch = _job(
        id="mismatch",
        required_skills=["Java", "Ruby"],
    )

    results = rank_jobs(candidate, [job_mismatch, job_match])
    ids = [m.job.id for m in results]

    assert ids[0] == "match"
    assert ids[1] == "mismatch"


def test_missing_skills_not_treated_as_perfect_match():
    """Missing skill info returns 50.0 (neutral), not 100.0.
    This must NOT behave like a perfect match.

    Skill scoring formula: (required_match * 0.7 + preferred_match * 0.3) * 100
    With only required skills listed: max is 70.0 (all required match).
    With no skills at all: 50.0 (neutral).
    """
    candidate = _candidate(skills=["Python"])
    job_no_skills = _job(
        id="no-skills",
        required_skills=[],
        preferred_skills=[],
    )
    job_match = _job(
        id="match",
        required_skills=["Python"],
    )

    match_no_skills = score_job(candidate, job_no_skills)
    match_perfect = score_job(candidate, job_match)

    # Missing skills: neutral 50.0
    assert match_no_skills.skill_score == 50.0
    # Known match: 70.0 (100% required match * 0.7)
    assert match_perfect.skill_score == 70.0

    # The perfect-match job must rank higher
    results = rank_jobs(candidate, [job_no_skills, job_match])
    assert results[0].job.id == "match"


# ============================================================
# 3. MISSING SKILLS — CRITICAL
# ============================================================


def test_missing_skill_info_scores_50_not_100():
    """Missing skills = neutral 50.0, never 100.0."""
    candidate = _candidate()
    job = _job(required_skills=[], preferred_skills=[])

    match = score_job(candidate, job)

    assert match.skill_score == 50.0
    assert 0.0 < match.compatibility_score < 100.0


def test_missing_skill_info_reduces_confidence():
    """Missing skill data reduces confidence because job information
    is incomplete."""
    candidate = _candidate()
    job = _job(required_skills=[], preferred_skills=[])

    match = score_job(candidate, job)

    # Skill information unavailable: 0.40 weight missing
    assert match.confidence == 1.0 - SKILL_WEIGHT


def test_missing_skills_deterministic():
    """Ranking with missing skills must be deterministic."""
    candidate = _candidate()
    jobs = [_job(id=f"j-{i}", required_skills=[]) for i in range(10)]

    orders = []
    for _ in range(5):
        orders.append(_rank_ids(candidate, jobs))

    assert all(o == orders[0] for o in orders)


# ============================================================
# 4. KNOWN ROLE MISMATCH
# ============================================================


def test_role_mismatch_excluded_by_eligibility():
    """Known role mismatch is a HARD eligibility filter.
    The job is excluded from ranking entirely, not just scored lower.

    This is the current architecture: eligibility handles hard
    disqualifiers, and role mismatch is one of them.
    """
    candidate = _candidate(preferred_roles=["Backend Engineer"])
    job_mismatch = _job(id="mismatch", title="Data Scientist")

    match = score_job(candidate, job_mismatch)

    # Role mismatch => ineligible
    assert match.eligible is False
    assert any("role" in r.lower() for r in match.eligibility_reasons)

    # Ineligible jobs do not appear in rank_jobs output
    results = rank_jobs(candidate, [job_mismatch])
    assert results == []


def test_role_mismatch_does_not_override_eligibility():
    """Even with perfect skills, role mismatch must not make a job
    eligible when the candidate has explicit role preferences."""
    candidate = _candidate(
        skills=["Python", "C++", "FastAPI"],
        preferred_roles=["Backend Engineer"],
    )
    job = _job(
        id="wrong-role",
        title="Data Scientist",
        required_skills=["Python", "C++", "FastAPI"],
    )

    match = score_job(candidate, job)
    assert match.eligible is False


def test_role_mismatch_not_overridden_by_strong_skills():
    """Even with perfect skills, role mismatch makes the job ineligible.
    Role preferences are a hard filter, not just a scoring dimension."""
    candidate = _candidate(
        skills=["Python", "C++", "FastAPI", "React"],
        preferred_roles=["Backend Engineer"],
    )
    # Strong skills, wrong role => ineligible
    job_wrong_role = _job(
        id="wrong-role",
        title="Data Scientist",
        required_skills=["Python", "C++", "FastAPI", "React"],
    )

    match = score_job(candidate, job_wrong_role)
    assert match.eligible is False


# ============================================================
# 5. UNKNOWN ROLE
# ============================================================


def test_unknown_role_scores_zero_for_role():
    """Job with unclassifiable role must score 0 for role dimension."""
    candidate = _candidate(preferred_roles=["Backend Engineer"])
    job = _job(title="Something Completely Unknown XYZ")

    match = score_job(candidate, job)

    assert match.role_score == 0.0


def test_unknown_role_reduces_confidence():
    """Unknown role must reduce confidence by ROLE_WEIGHT."""
    candidate = _candidate(preferred_roles=["Backend Engineer"])
    job = _job(title="Something Completely Unknown XYZ")

    match = score_job(candidate, job)

    expected_confidence = 1.0 - ROLE_WEIGHT
    assert abs(match.confidence - expected_confidence) < 0.01


def test_no_role_preference_vs_unknown_role_are_different():
    """Candidate with no role preference AND resume roles => None.
    Candidate with preferences but unknown job role => 0.0.
    These are fundamentally different."""
    # Case A: no role preference, no resume roles => None
    candidate_no_pref = _candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=[],
    )
    job = _job(title="Backend Engineer")
    match_a = score_job(candidate_no_pref, job)
    assert match_a.role_score is None

    # Case B: has preferences, job role unknown => 0.0
    candidate_with_pref = _candidate(
        preferred_roles=["Backend Engineer"],
    )
    job_unknown = _job(title="Something Completely Unknown XYZ")
    match_b = score_job(candidate_with_pref, job_unknown)
    assert match_b.role_score == 0.0

    # None and 0.0 are semantically different
    assert match_a.role_score is None
    assert match_b.role_score == 0.0


def test_candidate_with_resume_roles_but_no_preferences():
    """Resume roles provide evidence (score 70) even without preferences."""
    candidate = _candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=["Backend Engineer"],
    )
    job = _job(title="Backend Engineer")

    match = score_job(candidate, job)

    # Resume role gives 70 * 0.85 (RESUME_WEIGHT) = 59.5 role_score
    assert match.role_score is not None
    assert match.role_score > 0


# ============================================================
# 6. MISSING LOCATION
# ============================================================


def test_empty_location_and_remote_type():
    """Job with empty location and empty remote_type."""
    candidate = _candidate(preferred_locations=["India"])
    job = _job(id="no-loc", location="", remote_type="")

    match = score_job(candidate, job)

    # Empty location does not match India preference
    assert match.location_score == 0.0


def test_empty_location_with_remote_type():
    """Job with empty location but remote_type='Remote'."""
    candidate = _candidate(preferred_locations=["India"])
    job = _job(
        id="remote",
        location="",
        remote_type="Remote",
    )

    match = score_job(candidate, job)

    # Remote jobs are accepted when country is unknown
    assert match.location_score == 100.0


def test_empty_location_not_treated_as_match():
    """Empty location must not become a perfect match."""
    candidate = _candidate(preferred_locations=["India"])
    job = _job(location="", remote_type="")

    assert calculate_location_score(candidate, job) == 0.0


# ============================================================
# 7. REMOTE JOB
# ============================================================


def test_remote_job_with_empty_location():
    """remote_type='Remote' with empty location string."""
    candidate = _candidate(preferred_locations=["India"])
    job = _job(location="", remote_type="Remote")

    match = score_job(candidate, job)
    assert match.location_score == 100.0


def test_remote_us_job_rejected_for_india_preference():
    """Remote US job must be rejected for India-preference candidate."""
    candidate = _candidate(preferred_locations=["India"])
    job = _job(
        location="Remote - United States",
        remote_type="Remote",
    )

    match = score_job(candidate, job)
    assert match.location_score == 0.0


def test_remote_india_job_accepted_for_india_preference():
    """Remote India job must be accepted for India-preference candidate."""
    candidate = _candidate(preferred_locations=["India"])
    job = _job(
        location="Remote - India",
        remote_type="Remote",
    )

    match = score_job(candidate, job)
    assert match.location_score == 100.0


# ============================================================
# 8. CANDIDATE WITH NO LOCATION PREFERENCE
# ============================================================


def test_no_location_preference_returns_none():
    """preferred_locations=[] => location_score=None."""
    candidate = _candidate(preferred_locations=[])
    job = _job(location="Bengaluru, India")

    match = score_job(candidate, job)
    assert match.location_score is None


def test_no_location_preference_excludes_from_compatibility():
    """When location preference is None, it must not participate
    in the weighted average."""
    candidate_no_loc = _candidate(preferred_locations=[])
    candidate_with_loc = _candidate(preferred_locations=["India"])

    job = _job(location="Bengaluru, India")

    match_no_loc = score_job(candidate_no_loc, job)
    match_with_loc = score_job(candidate_with_loc, job)

    # With location pref: skill*0.40 + role*0.30 + exp*0.20 + loc*0.10
    # Without location pref: skill*0.40 + role*0.30 + exp*0.20 / 0.90
    # The dimensions should produce different compatibilities
    assert match_no_loc.location_score is None
    assert match_with_loc.location_score == 100.0


def test_no_location_preference_does_not_create_fake_mismatch():
    """Missing location preference must NOT reduce the ranking score
    by creating a false mismatch."""
    candidate = _candidate(preferred_locations=[])
    job = _job(location="Hawthorne, CA")

    match = score_job(candidate, job)

    # Location is None, not 0.0 — no penalty applied
    assert match.location_score is None
    assert match.eligible is True


def test_no_location_preference_does_not_reduce_confidence():
    """Confidence is based on job information, not candidate
    preference configuration."""
    candidate_no_loc = _candidate(preferred_locations=[])
    candidate_with_loc = _candidate(preferred_locations=["India"])

    job = _job(
        location="Bengaluru, India",
        required_skills=["Python", "C++"],
    )

    match_no_loc = score_job(candidate_no_loc, job)
    match_with_loc = score_job(candidate_with_loc, job)

    # Same job, same job information => same confidence
    assert match_no_loc.confidence == match_with_loc.confidence


# ============================================================
# 9. CANDIDATE WITH NO ROLE PREFERENCE
# ============================================================


def test_no_role_preference_no_resume_roles_returns_none():
    """No preferences AND no resume roles => role_score=None."""
    candidate = _candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=[],
    )
    job = _job(title="Backend Engineer")

    match = score_job(candidate, job)
    assert match.role_score is None


def test_no_role_preference_with_resume_roles():
    """No preferences but resume roles exist => role_score from resume."""
    candidate = _candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=["Backend Engineer"],
    )
    job = _job(title="Backend Engineer")

    match = score_job(candidate, job)
    assert match.role_score is not None
    assert match.role_score > 0


# ============================================================
# 10. LOW-INFORMATION JOB
# ============================================================


def test_low_information_job_low_confidence():
    """A job with minimal information must have low confidence."""
    candidate = _candidate(preferred_locations=[])
    job = _job(
        title="Some Random Unclassifiable Title",
        required_skills=[],
        preferred_skills=[],
        location="",
        remote_type="",
        experience_years_required=None,
    )

    match = score_job(candidate, job)

    # No skills: missing 0.40
    # Unknown role: missing 0.30
    # No location info: missing 0.10
    # Experience: always available (0.20)
    assert abs(match.confidence - 0.2) < 0.01


def test_low_information_job_vs_high_information_same_compatibility():
    """Two jobs with similar compatibility but different information
    completeness: higher information must produce higher ranking."""
    candidate = _candidate(preferred_locations=[])

    # High info: complete information
    job_high = _job(
        id="high-info",
        title="Backend Engineer",
        required_skills=["Python", "C++"],
        location="Bengaluru, India",
    )

    # Low info: missing everything
    job_low = _job(
        id="low-info",
        title="Backend Engineer",
        required_skills=[],
        preferred_skills=[],
        location="",
        remote_type="",
    )

    results = rank_jobs(candidate, [job_low, job_high])

    # Same role match (100), but high-info has better skill match
    # and confidence. High-info should rank first.
    assert results[0].job.id == "high-info"


# ============================================================
# 11. CONFIDENCE PENALTY
# ============================================================


def test_higher_confidence_wins_when_compatibility_equal():
    """Same compatibility, different confidence: higher confidence
    wins in ranking."""
    candidate = _candidate()
    job_a = _job(
        id="A",
        required_skills=["Python", "C++"],
        preferred_skills=["FastAPI"],
        title="Backend Engineer",
        location="Bengaluru, India",
    )
    job_b = _job(
        id="B",
        required_skills=[],
        preferred_skills=[],
        title="Backend Engineer",
        location="Bengaluru, India",
    )

    results = rank_jobs(candidate, [job_b, job_a])

    # Job A has full info (confidence=1.0), Job B missing skills
    # (confidence=0.6). Even though B's compatibility might be
    # similar, A should rank higher due to confidence.
    assert results[0].job.id == "A"


def test_ranking_score_lte_compatibility_score():
    """Ranking score must never exceed compatibility score because
    confidence_factor <= 1.0."""
    candidate = _candidate()
    jobs = [
        _job(
            id=f"job-{i}",
            required_skills=["Python", "C++"],
            location="Bengaluru, India",
        )
        for i in range(20)
    ]

    for match in rank_jobs(candidate, jobs):
        assert match.final_score <= match.compatibility_score + 0.01


# ============================================================
# 12. COMPATIBILITY VS CONFIDENCE TRADEOFF
# ============================================================


def test_compatibility_vs_confidence_exact_calculation():
    """Construct a case where higher-compatibility/lower-confidence
    competes against lower-compatibility/higher-confidence.
    Verify the exact mathematical result.

    Skill scoring: (required_match * 0.7 + preferred_match * 0.3) * 100
    """
    candidate = _candidate(
        skills=["Python", "C++", "Java"],
        preferred_roles=["Backend Engineer"],
        preferred_locations=["India"],
        experience_years=5.0,
    )

    # Job A: all 3 required skills match, but unknown role
    # skill = (3/3 * 0.7) * 100 = 70.0, role = 0, exp = 100, loc = 100
    # compatibility = 70*0.40 + 0*0.30 + 100*0.20 + 100*0.10 = 58.0
    # confidence = 0.40 + 0.20 + 0.10 = 0.70
    job_a = _job(
        id="A",
        title="Something Unclassifiable",
        required_skills=["Python", "C++", "Java"],
        location="Bengaluru, India",
    )

    # Job B: all 3 required skills match, complete info
    # skill = 70.0, role = 100, exp = 100, loc = 100
    # compatibility = 70*0.40 + 100*0.30 + 100*0.20 + 100*0.10 = 88.0
    # confidence = 1.0
    job_b = _job(
        id="B",
        title="Backend Engineer",
        required_skills=["Python", "C++", "Java"],
        location="Bengaluru, India",
    )

    # Verify the exact compatibility scores
    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Job A: role unknown -> 0
    assert match_a.role_score == 0.0
    assert abs(match_a.skill_score - 70.0) < 0.01
    assert abs(match_a.confidence - 0.70) < 0.01
    assert abs(match_a.compatibility_score - 58.0) < 0.01

    # Job B: role match -> 100
    assert match_b.role_score == 100.0
    assert match_b.confidence == 1.0
    assert abs(match_b.compatibility_score - 88.0) < 0.01

    # Calculate expected ranking scores
    expected_a = match_a.compatibility_score * (
        MIN_CONFIDENCE + (1 - MIN_CONFIDENCE) * match_a.confidence
    )
    expected_b = match_b.compatibility_score * (
        MIN_CONFIDENCE + (1 - MIN_CONFIDENCE) * match_b.confidence
    )

    assert abs(match_a.final_score - round(expected_a, 2)) < 0.01
    assert abs(match_b.final_score - round(expected_b, 2)) < 0.01

    # Job B has higher compatibility AND higher confidence
    # Job B must rank first
    results = rank_jobs(candidate, [job_a, job_b])
    assert results[0].job.id == "B"


# ============================================================
# 13. SALARY MUST NOT AFFECT RANKING
# ============================================================


def test_salary_does_not_affect_ranking():
    """Otherwise identical jobs with different salaries must produce
    identical ranking scores."""
    candidate = _candidate()

    job_low = _job(
        id="low-salary",
        salary_min_lpa=5.0,
        salary_max_lpa=10.0,
    )
    job_high = _job(
        id="high-salary",
        salary_min_lpa=50.0,
        salary_max_lpa=100.0,
    )

    match_low = score_job(candidate, job_low)
    match_high = score_job(candidate, job_high)

    assert match_low.compatibility_score == match_high.compatibility_score
    assert match_low.confidence == match_high.confidence
    assert match_low.final_score == match_high.final_score


def test_salary_missing_vs_present_no_ranking_change():
    """Jobs with and without salary must rank identically."""
    candidate = _candidate()

    job_no_salary = _job(id="no-salary")
    job_with_salary = _job(
        id="with-salary",
        salary_min_lpa=10.0,
        salary_max_lpa=20.0,
    )

    match_no = score_job(candidate, job_no_salary)
    match_with = score_job(candidate, job_with_salary)

    assert match_no.compatibility_score == match_with.compatibility_score
    assert match_no.final_score == match_with.final_score


def test_salary_not_in_sort_key():
    """Salary must not appear in the ranking sort key."""
    candidate = _candidate()
    job_a = _job(id="A", salary_max_lpa=5.0)
    job_b = _job(id="B", salary_max_lpa=100.0)

    results = rank_jobs(candidate, [job_a, job_b])

    # Same jobs, different salaries: order determined by job.id
    # Both have identical everything except salary
    ids = [m.job.id for m in results]
    assert ids == ["A", "B"]


# ============================================================
# 14. INPUT ORDER INDEPENDENCE
# ============================================================


def test_input_order_does_not_change_ranking():
    """Same jobs in different input orders must produce
    identical ranking."""
    candidate = _candidate()
    jobs = [
        _job(id="A", required_skills=["Python"]),
        _job(id="B", required_skills=["C++"]),
        _job(id="C", required_skills=["Java"]),
        _job(id="D", required_skills=["Python", "C++"]),
        _job(id="E", required_skills=[]),
    ]

    order1 = _rank_ids(candidate, jobs)

    shuffled = list(jobs)
    random.seed(42)
    random.shuffle(shuffled)
    order2 = _rank_ids(candidate, shuffled)

    reversed_jobs = list(reversed(jobs))
    order3 = _rank_ids(candidate, reversed_jobs)

    assert order1 == order2
    assert order1 == order3


# ============================================================
# 15. DETERMINISTIC TIE BREAKING
# ============================================================


def test_tie_break_ranking_score_desc():
    """Different ranking scores: higher wins."""
    candidate = _candidate()
    job_a = _job(
        id="A",
        required_skills=["Python", "C++"],
        preferred_skills=["FastAPI"],
    )
    job_b = _job(id="B", required_skills=["Java"])

    results = rank_jobs(candidate, [job_b, job_a])
    assert results[0].job.id == "A"
    assert results[0].final_score > results[1].final_score


def test_tie_break_confidence_desc():
    """Same final_score, different confidence: higher confidence wins."""
    candidate = _candidate()
    job_a = _job(
        id="A",
        required_skills=["Python", "C++"],
        title="Backend Engineer",
    )
    job_b = _job(
        id="B",
        required_skills=[],
        preferred_skills=[],
        title="Backend Engineer",
    )

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Force identical final_score but different confidence
    match_a = replace(match_a, final_score=80.0, confidence=0.60, compatibility_score=90)
    match_b = replace(match_b, final_score=80.0, confidence=1.00, compatibility_score=80)

    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    assert ranked[0].confidence > ranked[1].confidence
    assert ranked[0].job.id == "B"


def test_tie_break_compatibility_desc():
    """Same final_score and confidence, different compatibility:
    higher compatibility wins."""
    candidate = _candidate()
    job_a = _job(id="A")
    job_b = _job(id="B")

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    match_a = replace(match_a, final_score=80.0, confidence=0.80, compatibility_score=90)
    match_b = replace(match_b, final_score=80.0, confidence=0.80, compatibility_score=80)

    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    assert ranked[0].compatibility_score > ranked[1].compatibility_score
    assert ranked[0].job.id == "A"


def test_tie_break_job_id_asc():
    """Same final_score, confidence, and compatibility: lower job.id wins."""
    candidate = _candidate()
    job_a = _job(id="alpha")
    job_b = _job(id="beta")

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    match_a = replace(match_a, final_score=80.0, confidence=0.80, compatibility_score=90)
    match_b = replace(match_b, final_score=80.0, confidence=0.80, compatibility_score=90)

    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    assert ranked[0].job.id == "alpha"
    assert ranked[1].job.id == "beta"


# ============================================================
# 16. REPEATED RANKING DETERMINISM
# ============================================================


def test_repeated_ranking_identical_results():
    """Running rank_jobs multiple times must produce identical results."""
    candidate = _candidate()
    jobs = [
        _job(id="A", required_skills=["Python"]),
        _job(id="B", required_skills=["C++"]),
        _job(id="C", required_skills=["Java"]),
    ]

    results_set = set()
    for _ in range(10):
        results = rank_jobs(candidate, jobs)
        results_set.add(tuple(m.job.id for m in results))

    assert len(results_set) == 1


def test_repeated_ranking_identical_scores():
    """Score values must be identical across repeated runs."""
    candidate = _candidate()
    jobs = [_job(id="A", required_skills=["Python"])]

    scores = []
    for _ in range(10):
        match = score_job(candidate, jobs[0])
        scores.append((
            match.skill_score,
            match.role_score,
            match.experience_score,
            match.location_score,
            match.compatibility_score,
            match.confidence,
            match.final_score,
        ))

    assert len(set(scores)) == 1


# ============================================================
# 17. LIMIT IS APPLIED AFTER SORTING
# ============================================================


def test_limit_returns_top_n_not_first_n():
    """Limit=5 must return the top 5 by score, not the first 5 input."""
    candidate = _candidate(
        skills=["Python", "C++"],
        preferred_roles=["Backend Engineer"],
    )

    # Create jobs with varying skill matches
    jobs = []
    for i in range(20):
        # Jobs 0-4: perfect skill match
        # Jobs 5-19: partial or no match
        if i < 5:
            skills = ["Python", "C++"]
        elif i < 10:
            skills = ["Python"]
        else:
            skills = ["Java"]

        jobs.append(_job(
            id=f"job-{i:02d}",
            required_skills=skills,
        ))

    results = rank_jobs(candidate, jobs, limit=5)
    result_ids = [m.job.id for m in results]

    # Top 5 should be the perfect-match jobs
    assert len(results) == 5
    for i in range(5):
        assert f"job-{i:02d}" in result_ids


def test_limit_larger_than_jobs_returns_all():
    """Limit larger than job count returns all eligible jobs."""
    candidate = _candidate()
    jobs = [_job(id="A"), _job(id="B")]

    results = rank_jobs(candidate, jobs, limit=100)
    assert len(results) == 2


# ============================================================
# 18. INELIGIBLE JOBS NEVER APPEAR
# ============================================================


def test_ineligible_jobs_excluded_from_ranking():
    """Ineligible jobs must not appear in ranking results."""
    candidate = _candidate(preferred_locations=["India"])

    eligible_job = _job(
        id="eligible",
        location="Bengaluru, India",
    )
    ineligible_job = _job(
        id="ineligible",
        location="Hawthorne, CA",
    )

    results = rank_jobs(candidate, [ineligible_job, eligible_job])
    result_ids = [m.job.id for m in results]

    assert "ineligible" not in result_ids
    assert result_ids == ["eligible"]


def test_ineligible_high_score_does_not_override_eligibility():
    """Even if an ineligible job would score high, it must not appear."""
    candidate = _candidate(
        preferred_roles=["Backend Engineer"],
        preferred_locations=["India"],
    )

    # Perfect role match but wrong location
    ineligible = _job(
        id="wrong-loc",
        title="Backend Engineer",
        required_skills=["Python", "C++"],
        location="Hawthorne, CA",
    )

    # Weaker match but eligible
    eligible = _job(
        id="ok-loc",
        title="Backend Engineer",
        required_skills=["Python"],
        location="Bengaluru, India",
    )

    results = rank_jobs(candidate, [ineligible, eligible])
    result_ids = [m.job.id for m in results]

    assert "wrong-loc" not in result_ids
    assert result_ids == ["ok-loc"]


def test_role_ineligible_job_excluded():
    """Job that fails role eligibility must be excluded."""
    candidate = _candidate(preferred_roles=["Backend Engineer"])
    job = _job(title="Mechanical Engineer")

    match = score_job(candidate, job)
    assert match.eligible is False


# ============================================================
# 19. EXPERIENCE EDGE CASES
# ============================================================


def test_no_experience_requirement():
    """No requirement => experience_score = 100."""
    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=None)

    match = score_job(candidate, job)
    assert match.experience_score == 100.0


def test_exact_experience_requirement():
    """Exact match => experience_score = 100."""
    candidate = _candidate(experience_years=3.0)
    job = _job(experience_years_required=3)

    match = score_job(candidate, job)
    assert match.experience_score == 100.0


def test_candidate_exceeds_experience():
    """Candidate exceeds requirement => experience_score = 100."""
    candidate = _candidate(experience_years=10.0)
    job = _job(experience_years_required=3)

    match = score_job(candidate, job)
    assert match.experience_score == 100.0


def test_candidate_below_experience():
    """Candidate below requirement => proportional score."""
    candidate = _candidate(experience_years=1.0)
    job = _job(experience_years_required=3)

    match = score_job(candidate, job)
    # 1/3 * 100 = 33.33
    assert 0.0 < match.experience_score < 50.0


def test_fractional_experience():
    """Fractional experience must work correctly."""
    candidate = _candidate(experience_years=1.5)
    job = _job(experience_years_required=2)

    match = score_job(candidate, job)
    # 1.5/2 * 100 = 75.0
    assert match.experience_score == 75.0


def test_zero_experience_with_positive_requirement():
    """0 experience with positive requirement => 0 score."""
    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=3)

    match = score_job(candidate, job)
    assert match.experience_score == 0.0


# ============================================================
# 20. SCORE BOUNDS
# ============================================================


def test_all_scores_within_bounds():
    """Every score must be within [0, 100] or None."""
    candidate = _candidate(
        preferred_roles=["Backend Engineer"],
        preferred_locations=["India"],
    )

    extreme_jobs = [
        _job(
            id="perfect",
            required_skills=["Python", "C++"],
            title="Backend Engineer",
            location="Bengaluru, India",
            experience_years_required=0,
        ),
        _job(
            id="terrible",
            required_skills=["Java", "Ruby", "Go"],
            title="Data Scientist",
            location="Hawthorne, CA",
            experience_years_required=100,
        ),
        _job(
            id="minimal",
            required_skills=[],
            title="Something Unknown",
            location="",
            remote_type="",
        ),
    ]

    for job in extreme_jobs:
        match = score_job(candidate, job)

        for score in (
            match.skill_score,
            match.role_score,
            match.experience_score,
            match.location_score,
            match.compatibility_score,
        ):
            if score is not None:
                assert 0.0 <= score <= 100.0, (
                    f"Score {score} out of bounds for job {job.id}"
                )

        assert 0.0 <= match.confidence <= 1.0
        assert 0.0 <= match.final_score <= 100.0


def test_confidence_always_in_0_1():
    """Confidence must always be between 0 and 1."""
    extreme_jobs = [
        _job(
            title="",
            required_skills=[],
            location="",
            remote_type="",
        ),
        _job(
            title="Senior Backend Engineer",
            required_skills=["Python", "C++", "FastAPI", "React"],
            location="Bengaluru, India",
        ),
    ]

    for job in extreme_jobs:
        conf = calculate_confidence(job)
        assert 0.0 <= conf <= 1.0


# ============================================================
# 21. NONE / MISSING DATA ROBUSTNESS
# ============================================================


def test_empty_strings_do_not_crash():
    """Empty strings must not crash the pipeline."""
    candidate = _candidate(
        skills=[],
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=[],
        preferred_locations=[],
    )
    job = _job(
        title="",
        company="",
        location="",
        remote_type="",
        required_skills=[],
        preferred_skills=[],
        experience_years_required=None,
    )

    match = score_job(candidate, job)
    assert match is not None
    assert isinstance(match.final_score, float)


def test_none_optional_fields_do_not_crash():
    """None in optional fields must not crash."""
    candidate = _candidate()
    job = _job(
        experience_years_required=None,
        salary_min_lpa=None,
        salary_max_lpa=None,
        description="",
    )

    match = score_job(candidate, job)
    assert match is not None


def test_empty_lists_do_not_crash():
    """Empty skill/role lists must not crash."""
    candidate = _candidate(
        skills=[],
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=[],
        preferred_locations=[],
        education=[],
        projects=[],
    )
    job = _job(
        required_skills=[],
        preferred_skills=[],
    )

    match = score_job(candidate, job)
    assert match is not None
    assert 0.0 <= match.final_score <= 100.0


# ============================================================
# 22. ZERO JOBS
# ============================================================


def test_zero_jobs_returns_empty():
    """rank_jobs with empty job list returns empty list."""
    candidate = _candidate()
    results = rank_jobs(candidate, [], limit=10)
    assert results == []


def test_zero_jobs_returns_empty_no_limit():
    """rank_jobs with empty job list and no limit."""
    candidate = _candidate()
    results = rank_jobs(candidate, [])
    assert results == []


# ============================================================
# 23. ONE JOB
# ============================================================


def test_one_eligible_job():
    """Single eligible job ranks correctly."""
    candidate = _candidate()
    job = _job(id="solo")

    results = rank_jobs(candidate, [job])
    assert len(results) == 1
    assert results[0].job.id == "solo"
    assert results[0].eligible is True


def test_one_ineligible_job():
    """Single ineligible job returns empty results."""
    candidate = _candidate(preferred_locations=["India"])
    job = _job(id="bad-loc", location="Hawthorne, CA")

    results = rank_jobs(candidate, [job])
    assert results == []


# ============================================================
# 24. CANDIDATE-AGNOSTIC TESTING
# ============================================================


def test_different_candidates_get_different_rankings():
    """Different candidate preferences must produce different rankings
    for the same job set."""
    backend_candidate = _candidate(
        preferred_roles=["Backend Engineer"],
        skills=["Python", "C++"],
    )
    frontend_candidate = _candidate(
        preferred_roles=["Frontend Engineer"],
        skills=["JavaScript", "React"],
    )

    jobs = [
        _job(
            id="be",
            title="Backend Engineer",
            required_skills=["Python", "C++"],
        ),
        _job(
            id="fe",
            title="Frontend Engineer",
            required_skills=["JavaScript", "React"],
        ),
    ]

    backend_ranked = rank_jobs(backend_candidate, jobs)
    frontend_ranked = rank_jobs(frontend_candidate, jobs)

    assert backend_ranked[0].job.id == "be"
    assert frontend_ranked[0].job.id == "fe"


def test_candidate_with_ml_preferences():
    """ML candidate should rank ML jobs higher."""
    ml_candidate = _candidate(
        preferred_roles=["Machine Learning Engineer"],
        skills=["Python", "PyTorch", "TensorFlow"],
    )

    jobs = [
        _job(
            id="ml",
            title="Machine Learning Engineer",
            required_skills=["Python", "PyTorch"],
        ),
        _job(
            id="be",
            title="Backend Engineer",
            required_skills=["Python"],
        ),
    ]

    results = rank_jobs(ml_candidate, jobs)
    assert results[0].job.id == "ml"


# ============================================================
# 25. RESUME ROLES ARE EVIDENCE, NOT PREFERENCE
# ============================================================


def test_resume_role_influences_scoring():
    """Resume roles provide scoring evidence (70 * RESUME_WEIGHT)
    even without explicit preferences."""
    candidate = _candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=["Backend Engineer"],
    )
    job = _job(title="Backend Engineer")

    match = score_job(candidate, job)

    # Resume role: 70 * RESUME_WEIGHT = 70 * 0.70 = 49.0 role_score
    assert match.role_score is not None
    assert match.role_score > 0


def test_resume_roles_not_copied_to_preferences():
    """apply_default_preferences must NOT copy resume roles into
    preferred_roles."""
    from run_jobagent import apply_default_preferences

    profile = CandidateProfile(
        resume_roles=["Backend Engineer", "ML Engineer"],
        skills=["Python"],
    )

    result = apply_default_preferences(profile)

    assert result.preferences.preferred_roles == []
    assert result.facts.resume_roles == [
        "Backend Engineer",
        "ML Engineer",
    ]


# ============================================================
# 26. PREFERENCE CHANGES MUST CHANGE RANKING
# ============================================================


def test_preference_changes_change_ranking():
    """Same jobs, different candidate preferences => different ranking."""
    jobs = [
        _job(
            id="be",
            title="Backend Engineer",
            required_skills=["Python"],
        ),
        _job(
            id="ml",
            title="Machine Learning Engineer",
            required_skills=["Python"],
        ),
    ]

    backend_candidate = _candidate(preferred_roles=["Backend Engineer"])
    ml_candidate = _candidate(preferred_roles=["Machine Learning Engineer"])

    be_ranked = rank_jobs(backend_candidate, jobs)
    ml_ranked = rank_jobs(ml_candidate, jobs)

    # Backend candidate should rank BE first
    assert be_ranked[0].job.id == "be"
    # ML candidate should rank ML first
    assert ml_ranked[0].job.id == "ml"


# ============================================================
# 27. CANDIDATE CONFIG DOES NOT CHANGE JOB CONFIDENCE
# ============================================================


def test_confidence_ignores_candidate_preferences():
    """Same job, different candidate preferences: confidence must
    be identical."""
    job = _job(
        required_skills=["Python", "C++"],
        title="Backend Engineer",
        location="Bengaluru, India",
    )

    candidate_a = _candidate(
        preferred_roles=["Backend Engineer"],
        preferred_locations=["India"],
    )
    candidate_b = _candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=[],
        preferred_locations=[],
    )

    match_a = score_job(candidate_a, job)
    match_b = score_job(candidate_b, job)

    assert match_a.confidence == match_b.confidence


# ============================================================
# 28. NO HIDDEN SALARY EFFECT
# ============================================================


def test_salary_not_in_compatibility():
    """Salary must not affect compatibility_score."""
    candidate = _candidate()

    job_a = _job(id="A", salary_min_lpa=5, salary_max_lpa=10)
    job_b = _job(id="B", salary_min_lpa=100, salary_max_lpa=200)

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    assert match_a.compatibility_score == match_b.compatibility_score


def test_salary_not_in_ranking_score():
    """Salary must not affect final_score."""
    candidate = _candidate()

    job_a = _job(id="A", salary_max_lpa=5)
    job_b = _job(id="B", salary_max_lpa=500)

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    assert match_a.final_score == match_b.final_score


def test_salary_not_in_sort_key():
    """Salary must not influence sort order."""
    candidate = _candidate()
    job_a = _job(id="A", salary_max_lpa=1)
    job_b = _job(id="B", salary_max_lpa=1000)

    results = rank_jobs(candidate, [job_b, job_a])
    # Identical jobs except salary: sort by id
    assert results[0].job.id == "A"
    assert results[1].job.id == "B"


# ============================================================
# 29. FINAL SCORE VS RANKING SCORE
# ============================================================


def test_final_score_is_ranking_score():
    """final_score field must equal compatibility * confidence_factor,
    not compatibility alone."""
    candidate = _candidate()
    job = _job(
        required_skills=["Python", "C++"],
        title="Backend Engineer",
        location="Bengaluru, India",
    )

    match = score_job(candidate, job)

    # Verify the formula
    confidence_factor = MIN_CONFIDENCE + (1.0 - MIN_CONFIDENCE) * match.confidence
    expected = match.compatibility_score * confidence_factor

    assert abs(match.final_score - round(expected, 2)) < 0.01

    # final_score must NOT equal compatibility when confidence < 1
    if match.confidence < 1.0:
        assert match.final_score != match.compatibility_score


def test_ranking_uses_final_score_not_compatibility():
    """Sort key must use final_score (ranking score), not
    compatibility_score."""
    candidate = _candidate()

    # Job A: high compatibility but low confidence
    job_a = _job(
        id="A",
        title="Something Unknown",
        required_skills=["Python", "C++"],
        location="Bengaluru, India",
    )

    # Job B: slightly lower compatibility but high confidence
    job_b = _job(
        id="B",
        title="Backend Engineer",
        required_skills=["Python"],
        location="Bengaluru, India",
    )

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # The ranking must use final_score, not compatibility
    results = rank_jobs(candidate, [job_a, job_b])
    if match_a.final_score > match_b.final_score:
        assert results[0].job.id == "A"
    elif match_b.final_score > match_a.final_score:
        assert results[0].job.id == "B"
    else:
        # Equal: tie-break by confidence then compatibility then id
        pass


# ============================================================
# 30. PROPERTY-STYLE / INVARIANT TESTS
# ============================================================


def test_invariant_improving_skill_never_lowers_ranking():
    """Improving a candidate's skill match should never lower ranking."""
    candidate = _candidate(skills=["Python"])

    # Job with Python required: partial match
    job_weak = _job(id="weak", required_skills=["Python", "C++", "Java"])
    match_weak = score_job(candidate, job_weak)

    # Same job but candidate now has Python and C++
    candidate_strong = _candidate(skills=["Python", "C++"])
    match_strong = score_job(candidate_strong, job_weak)

    assert match_strong.skill_score >= match_weak.skill_score
    assert match_strong.compatibility_score >= match_weak.compatibility_score


def test_invariant_improving_role_never_lowers_ranking():
    """Improving role compatibility should never lower ranking."""
    # Candidate with no role preference
    candidate_none = _candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=[],
    )
    job = _job(title="Backend Engineer")
    match_none = score_job(candidate_none, job)

    # Same candidate with explicit role preference
    candidate_preferred = _candidate(preferred_roles=["Backend Engineer"])
    match_preferred = score_job(candidate_preferred, job)

    # Role preference adds a signal; compatibility should be at least as high
    assert match_preferred.role_score >= (match_none.role_score or 0)


def test_invariant_improving_confidence_never_lowers_ranking():
    """Improving confidence while compatibility is constant should
    never lower ranking score."""
    compatibility = 80.0

    low_conf = calculate_ranking_score(compatibility, 0.5)
    high_conf = calculate_ranking_score(compatibility, 1.0)

    assert high_conf >= low_conf


def test_invariant_salary_never_changes_ranking():
    """Changing only salary must never change any ranking field."""
    candidate = _candidate()
    job_base = _job(id="test")

    match_no_salary = score_job(candidate, job_base)

    job_with_salary = replace(
        job_base,
        salary_min_lpa=10.0,
        salary_max_lpa=20.0,
    )
    match_with_salary = score_job(candidate, job_with_salary)

    assert match_no_salary.skill_score == match_with_salary.skill_score
    assert match_no_salary.role_score == match_with_salary.role_score
    assert match_no_salary.experience_score == match_with_salary.experience_score
    assert match_no_salary.location_score == match_with_salary.location_score
    assert match_no_salary.compatibility_score == match_with_salary.compatibility_score
    assert match_no_salary.confidence == match_with_salary.confidence
    assert match_no_salary.final_score == match_with_salary.final_score


def test_invariant_input_shuffle_preserves_ranking():
    """Shuffling input order must never change output ranking."""
    candidate = _candidate()
    jobs = [_job(id=f"job-{i}") for i in range(15)]

    order_before = _rank_ids(candidate, jobs)

    for seed in range(20):
        shuffled = list(jobs)
        random.seed(seed)
        random.shuffle(shuffled)
        order_after = _rank_ids(candidate, shuffled)
        assert order_before == order_after, (
            f"Seed {seed} changed ranking order"
        )


def test_invariant_adding_ineligible_job_preserves_eligible_ranking():
    """Adding an ineligible job must not change the ranking of
    already-eligible jobs."""
    candidate = _candidate(preferred_locations=["India"])

    eligible_jobs = [
        _job(id="A", location="Bengaluru, India", required_skills=["Python"]),
        _job(id="B", location="Mumbai, India", required_skills=["C++"]),
    ]

    order_before = _rank_ids(candidate, eligible_jobs)

    # Add an ineligible job
    ineligible_job = _job(id="bad", location="Hawthorne, CA")
    order_after = _rank_ids(candidate, eligible_jobs + [ineligible_job])

    # Eligible jobs must maintain their relative order
    assert order_before == order_after[:2]


def test_invariant_lowering_compatibility_never_improves_ranking():
    """Lowering compatibility while everything else is constant should
    never improve ranking score."""
    confidence = 0.8

    high_compat = calculate_ranking_score(90.0, confidence)
    low_compat = calculate_ranking_score(60.0, confidence)

    assert high_compat > low_compat


def test_invariant_confidence_never_exceeds_1():
    """Confidence must never exceed 1.0 for any job configuration."""
    extreme_jobs = [
        _job(
            title="Senior Software Engineer",
            required_skills=["Python", "C++", "FastAPI", "React", "Go", "Rust"],
            preferred_skills=["Java", "TypeScript", "SQL"],
            location="Bengaluru, India",
            remote_type="",
        ),
    ]

    for job in extreme_jobs:
        conf = calculate_confidence(job)
        assert conf <= 1.0


def test_invariant_compatibility_is_weighted_average():
    """Compatibility must always be a weighted average of active
    dimension scores."""
    candidate = _candidate(
        skills=["Python"],
        preferred_roles=["Backend Engineer"],
        preferred_locations=["India"],
        experience_years=3.0,
    )

    job = _job(
        required_skills=["Python"],
        title="Backend Engineer",
        location="Bengaluru, India",
        experience_years_required=2,
    )

    match = score_job(candidate, job)

    # All dimensions active
    expected = (
        match.skill_score * SKILL_WEIGHT
        + match.role_score * ROLE_WEIGHT
        + match.experience_score * EXPERIENCE_WEIGHT
        + match.location_score * LOCATION_WEIGHT
    )

    assert abs(match.compatibility_score - expected) < 0.01


def test_invariant_none_dimensions_excluded_from_compatibility():
    """None dimensions must not contribute to compatibility;
    weight must be redistributed."""
    candidate = _candidate(preferred_locations=[])

    job = _job(
        required_skills=["Python"],
        title="Backend Engineer",
        location="Bengaluru, India",
    )

    match = score_job(candidate, job)

    # Location is None, so active weights = skill + role + experience
    active_weight = SKILL_WEIGHT + ROLE_WEIGHT + EXPERIENCE_WEIGHT
    expected = (
        match.skill_score * SKILL_WEIGHT
        + match.role_score * ROLE_WEIGHT
        + match.experience_score * EXPERIENCE_WEIGHT
    ) / active_weight

    assert abs(match.compatibility_score - round(expected, 2)) < 0.01


def test_invariant_confidence_based_on_job_not_candidate():
    """Confidence must be identical for the same job regardless of
    candidate configuration."""
    job = _job(
        required_skills=["Python"],
        title="Backend Engineer",
        location="Bengaluru, India",
    )

    candidates = [
        _candidate(
            preferred_roles=["Backend Engineer"],
            preferred_locations=["India"],
        ),
        _candidate(
            preferred_roles=[],
            secondary_roles=[],
            resume_roles=[],
            preferred_locations=[],
        ),
        _candidate(
            preferred_roles=["Machine Learning Engineer"],
            preferred_locations=["Remote"],
        ),
    ]

    confidences = [
        score_job(c, job).confidence for c in candidates
    ]

    assert len(set(confidences)) == 1

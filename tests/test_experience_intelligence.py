"""
STEP 8.5 — Experience Intelligence tests.

Tests for the experience handling improvements:
- Internship vs full-time experience distinction
- Requirement strictness classification
- Experience risk classification
- Experience mismatch as soft signal (NOT hard eligibility)
- Risk as explanation (NOT ranking penalty)
- None vs 0 semantics
- Candidate-agnostic behavior
"""

from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.scoring.experience_scorer import (
    calculate_experience_score,
    classify_experience_risk,
)
from app.scoring.final_scorer import rank_jobs, score_job
from app.services.experience_parser import (
    classify_requirement_strictness,
    parse_experience_years,
)
from app.eligibility.eligibility import check_eligibility


# ============================================================
# HELPERS
# ============================================================


def _candidate(**kwargs):
    defaults = {
        "name": "Test User",
        "email": "test@example.com",
        "experience_years": 0.0,
        "skills": ["Python"],
    }
    defaults.update(kwargs)
    return CandidateProfile(**defaults)


def _job(**kwargs):
    defaults = {
        "id": "job-1",
        "title": "Software Engineer",
        "company": "TestCo",
        "location": "Bengaluru, India",
        "required_skills": ["Python"],
    }
    defaults.update(kwargs)
    return Job(**defaults)


# ============================================================
# 1. EXPERIENCE SCORE: 0 vs 2
# ============================================================


def test_zero_years_vs_two_years():
    """0 years vs 2+ requirement => score 0.0."""
    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 0.0


# ============================================================
# 2. EXPERIENCE SCORE: 1 vs 2
# ============================================================


def test_one_year_vs_two_years():
    """1 year vs 2+ requirement => proportional 50.0."""
    candidate = _candidate(experience_years=1)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 50.0


# ============================================================
# 3. EXPERIENCE SCORE: 2 vs 2
# ============================================================


def test_two_years_vs_two_years():
    """2 years vs 2+ requirement => 100.0 (met)."""
    candidate = _candidate(experience_years=2)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 4. EXPERIENCE SCORE: 3 vs 2
# ============================================================


def test_three_years_vs_two_years():
    """3 years vs 2+ requirement => 100.0 (exceeds)."""
    candidate = _candidate(experience_years=3)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 5. EXPERIENCE SCORE: 5 vs 2 (far exceeds)
# ============================================================


def test_five_years_vs_two_years():
    """5 years vs 2+ requirement => 100.0 (far exceeds)."""
    candidate = _candidate(experience_years=5)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 6. NO EXPERIENCE REQUIREMENT
# ============================================================


def test_no_experience_requirement():
    """No requirement => 100.0 (no constraint)."""
    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=None)

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 7. UNKNOWN EXPERIENCE REQUIREMENT
# ============================================================


def test_unknown_experience_requirement():
    """Unknown requirement => 100.0 (no constraint)."""
    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=None, experience_required="")

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 8. INTERNSHIP EXPERIENCE PRESENT
# ============================================================


def test_internship_experience_tracked_separately():
    """Internship years are tracked but do NOT automatically
    substitute for professional experience in scoring."""
    candidate = _candidate(
        experience_years=0,
        internship_years=1.0,
    )
    job = _job(experience_years_required=2)

    # Score uses professional experience (0), not internship (1)
    score = calculate_experience_score(candidate, job)
    assert score == 0.0

    # But internship data is preserved
    assert candidate.facts.internship_years == 1.0
    assert candidate.facts.experience_years == 0


def test_internship_years_none_semantics():
    """internship_years=None means unknown, not zero."""
    candidate = _candidate(experience_years=0)
    assert candidate.facts.internship_years is None

    candidate_with = _candidate(
        experience_years=0,
        internship_years=0.0,
    )
    assert candidate_with.facts.internship_years == 0.0

    # None and 0.0 are semantically different
    assert candidate.facts.internship_years is None
    assert candidate_with.facts.internship_years == 0.0


# ============================================================
# 9. FULL-TIME EXPERIENCE PRESENT
# ============================================================


def test_full_time_experience_used_for_scoring():
    """Professional experience_years is the primary scoring signal."""
    candidate = _candidate(experience_years=3)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 10. RELEVANT EXPERIENCE PRESENT
# ============================================================


def test_relevant_experience_contributes():
    """experience_years represents relevant professional experience."""
    candidate = _candidate(experience_years=2)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 11. INTERNSHIP + FULL-TIME EXPERIENCE
# ============================================================


def test_internship_plus_fulltime():
    """When both internship and full-time exist, scoring uses
    professional experience only."""
    candidate = _candidate(
        experience_years=2,
        internship_years=1.0,
    )
    job = _job(experience_years_required=3)

    # 2/3 * 100 = 66.67
    score = calculate_experience_score(candidate, job)
    assert abs(score - 66.67) < 0.01


# ============================================================
# 12. CANDIDATE EXPERIENCE EXPLICITLY ZERO
# ============================================================


def test_experience_explicitly_zero():
    """experience_years=0.0 is explicit zero, not unknown."""
    candidate = _candidate(experience_years=0.0)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    assert score == 0.0


# ============================================================
# 13. CANDIDATE EXPERIENCE UNKNOWN
# ============================================================


def test_experience_unknown():
    """experience_years defaults to 0.0 (zero, not None)."""
    candidate = _candidate()
    assert candidate.facts.experience_years == 0.0


# ============================================================
# 14. JOB SAYS "PREFERRED"
# ============================================================


def test_preferred_requirement_strictness():
    """'preferred' wording => preferred strictness."""
    strictness = classify_requirement_strictness(
        "2+ years preferred"
    )
    assert strictness == "preferred"


def test_nice_to_have_strictness():
    """'nice-to-have' wording => preferred strictness."""
    strictness = classify_requirement_strictness(
        "2+ years nice-to-have"
    )
    assert strictness == "preferred"


def test_plus_strictness():
    """'plus' wording => preferred strictness."""
    strictness = classify_requirement_strictness(
        "2+ years experience, Python a plus"
    )
    assert strictness == "preferred"


# ============================================================
# 15. JOB SAYS "REQUIRED"
# ============================================================


def test_required_requirement_strictness():
    """Standard numeric requirement => required strictness."""
    strictness = classify_requirement_strictness(
        "2+ years of experience"
    )
    assert strictness == "required"


def test_explicit_required_strictness():
    """'required' keyword => strict strictness."""
    strictness = classify_requirement_strictness(
        "2+ years required"
    )
    assert strictness == "strict"


def test_must_have_strictness():
    """'must have' keyword => strict strictness."""
    strictness = classify_requirement_strictness(
        "Must have 5+ years of experience"
    )
    assert strictness == "strict"


def test_mandatory_strictness():
    """'mandatory' keyword => strict strictness."""
    strictness = classify_requirement_strictness(
        "3+ years mandatory"
    )
    assert strictness == "strict"


# ============================================================
# 16. AMBIGUOUS REQUIREMENT WORDING
# ============================================================


def test_ambiguous_wording_returns_unknown():
    """Ambiguous or missing wording => unknown strictness."""
    strictness = classify_requirement_strictness("")
    assert strictness == "unknown"

    # "experience preferred" contains "preferred" keyword
    # => classified as "preferred" (correct behavior)
    strictness = classify_requirement_strictness("experience preferred")
    assert strictness == "preferred"


# ============================================================
# 17. EXPERIENCE MISMATCH DOES NOT CAUSE ELIGIBILITY REJECTION
# ============================================================


def test_experience_mismatch_not_hard_rejection():
    """Experience gap is a soft signal, NOT a hard eligibility filter."""
    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=10)

    eligibility = check_eligibility(candidate, job)

    # Job is still eligible despite 10-year experience gap
    assert eligibility.eligible is True

    # But there is a warning reason
    assert any(
        "experience" in r.lower()
        for r in eligibility.reasons
    )


def test_experience_gap_in_reasons_not_eligibility():
    """Experience gap appears in reasons but does not affect
    the eligible flag."""
    candidate = _candidate(experience_years=1)
    job = _job(experience_years_required=5)

    match = score_job(candidate, job)

    assert match.eligible is True
    assert any(
        "experience" in r.lower()
        for r in match.eligibility_reasons
    )


# ============================================================
# 18. EXPERIENCE RISK DOES NOT DIRECTLY MODIFY RANKING
# ============================================================


def test_experience_risk_does_not_modify_ranking():
    """experience_risk is explanation-only. Two jobs with the same
    compatibility must have the same final_score regardless of risk."""
    candidate = _candidate(experience_years=1)

    job_a = _job(
        id="A",
        experience_years_required=2,
        requirement_strictness="required",
    )
    job_b = _job(
        id="B",
        experience_years_required=2,
        requirement_strictness="preferred",
    )

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Same compatibility and final_score (risk is explanation-only)
    assert match_a.compatibility_score == match_b.compatibility_score
    assert match_a.final_score == match_b.final_score

    # But different risk
    assert match_a.experience_risk != match_b.experience_risk


def test_risk_in_job_match_but_not_in_sort_key():
    """experience_risk is in JobMatch but not used for ranking."""
    candidate = _candidate(experience_years=0)

    job_a = _job(
        id="A",
        experience_years_required=2,
        requirement_strictness="strict",
    )
    job_b = _job(
        id="B",
        experience_years_required=2,
        requirement_strictness="preferred",
    )

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Risk differs
    assert match_a.experience_risk != match_b.experience_risk

    # But final_score is identical
    assert match_a.final_score == match_b.final_score


# ============================================================
# 19. SALARY DOES NOT BECOME INVOLVED
# ============================================================


def test_salary_not_involved_in_experience():
    """Salary does not affect experience scoring or risk."""
    candidate = _candidate(experience_years=1)

    job_a = _job(
        id="A",
        experience_years_required=2,
        salary_min_lpa=5,
        salary_max_lpa=10,
    )
    job_b = _job(
        id="B",
        experience_years_required=2,
        salary_min_lpa=100,
        salary_max_lpa=200,
    )

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    assert match_a.experience_score == match_b.experience_score
    assert match_a.experience_risk == match_b.experience_risk
    assert match_a.final_score == match_b.final_score


# ============================================================
# 20. CANDIDATE-AGNOSTIC BEHAVIOR
# ============================================================


def test_experience_scoring_is_candidate_agnostic():
    """Same job, different candidates => different scores
    based purely on experience_years."""
    job = _job(experience_years_required=3)

    junior = _candidate(experience_years=1)
    mid = _candidate(experience_years=3)
    senior = _candidate(experience_years=8)

    score_junior = calculate_experience_score(junior, job)
    score_mid = calculate_experience_score(mid, job)
    score_senior = calculate_experience_score(senior, job)

    assert score_junior < score_mid
    assert score_mid == score_senior == 100.0


# ============================================================
# 21. EXPERIENCE RISK CLASSIFICATION
# ============================================================


def test_risk_low_when_meets_requirement():
    """Meets requirement => LOW risk."""
    risk = classify_experience_risk(3.0, 2.0, "required")
    assert risk == "low"


def test_risk_low_when_exceeds():
    """Exceeds requirement => LOW risk."""
    risk = classify_experience_risk(5.0, 2.0, "required")
    assert risk == "low"


def test_risk_medium_slightly_below_strict():
    """Slightly below strict requirement => MEDIUM risk."""
    risk = classify_experience_risk(1.8, 2.0, "strict")
    assert risk == "medium"


def test_risk_high_substantially_below_strict():
    """Substantially below strict requirement => HIGH risk."""
    risk = classify_experience_risk(0.5, 2.0, "strict")
    assert risk == "high"


def test_risk_low_slightly_below_required():
    """Slightly below required => LOW risk (standard)."""
    risk = classify_experience_risk(1.8, 2.0, "required")
    assert risk == "low"


def test_risk_medium_modestly_below_required():
    """Modestly below required => MEDIUM risk."""
    risk = classify_experience_risk(1.0, 2.0, "required")
    assert risk == "medium"


def test_risk_high_far_below_required():
    """Far below required => HIGH risk."""
    risk = classify_experience_risk(0.5, 3.0, "required")
    assert risk == "high"


def test_risk_low_preferred():
    """Preferred requirement: even 50% gap is LOW risk."""
    risk = classify_experience_risk(1.0, 2.0, "preferred")
    assert risk == "low"


def test_risk_medium_preferred_large_gap():
    """Preferred requirement, large gap => MEDIUM risk."""
    risk = classify_experience_risk(0.5, 3.0, "preferred")
    assert risk == "medium"


def test_risk_unknown_strictness():
    """Unknown strictness: moderate gap => MEDIUM risk."""
    risk = classify_experience_risk(1.0, 2.0, "unknown")
    assert risk == "medium"


def test_risk_unknown_no_requirement():
    """No requirement => UNKNOWN risk."""
    risk = classify_experience_risk(5.0, None, "required")
    assert risk == "unknown"


# ============================================================
# 22. SCORE BOUNDS
# ============================================================


def test_experience_score_always_in_bounds():
    """Experience score must always be 0-100."""
    extreme_cases = [
        (0, 100),
        (0.5, 2),
        (1, 2),
        (2, 2),
        (100, 2),
        (0, None),
    ]

    for cand_yrs, req_yrs in extreme_cases:
        candidate = _candidate(experience_years=cand_yrs)
        job = _job(experience_years_required=req_yrs)
        score = calculate_experience_score(candidate, job)
        assert 0.0 <= score <= 100.0, (
            f"Score {score} out of bounds for "
            f"cand={cand_yrs}, req={req_yrs}"
        )


# ============================================================
# 23. EXPLANATION INCLUDES RISK
# ============================================================


def test_explanation_includes_risk_for_mismatch():
    """Experience mismatch explanation includes risk context."""
    from app.scoring.explanation import explain_experience_match

    candidate = _candidate(experience_years=1)
    job = _job(
        experience_years_required=3,
        requirement_strictness="required",
    )

    explanation = explain_experience_match(candidate, job)

    assert "not met" in explanation
    # Risk context is included via "may be screened" or similar
    assert "screened" in explanation.lower() or "risk" in explanation.lower()


def test_explanation_no_risk_when_met():
    """Experience met explanation does NOT include risk."""
    from app.scoring.explanation import explain_experience_match

    candidate = _candidate(experience_years=5)
    job = _job(experience_years_required=2)

    explanation = explain_experience_match(candidate, job)

    assert "met" in explanation
    assert "risk" not in explanation.lower()


def test_explanation_no_requirement():
    """No requirement explanation is clean."""
    from app.scoring.explanation import explain_experience_match

    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=None)

    explanation = explain_experience_match(candidate, job)
    assert "No explicit requirement" in explanation


# ============================================================
# 24. INTERNSHIP IN CANDIDATE PROFILE
# ============================================================


def test_internship_years_in_profile():
    """internship_years is a valid CandidateFacts field."""
    candidate = _candidate(
        experience_years=0,
        internship_years=1.0,
    )

    assert candidate.facts.internship_years == 1.0
    assert candidate.facts.experience_years == 0.0


def test_internship_years_not_affecting_scoring():
    """Internship data exists but does not change score."""
    job = _job(experience_years_required=2)

    cand_no_intern = _candidate(
        experience_years=1,
        internship_years=None,
    )
    cand_with_intern = _candidate(
        experience_years=1,
        internship_years=1.0,
    )

    score_no = calculate_experience_score(cand_no_intern, job)
    score_with = calculate_experience_score(cand_with_intern, job)

    assert score_no == score_with == 50.0


# ============================================================
# 25. REQUIREMENT STRICTNESS ON JOB
# ============================================================


def test_requirement_strictness_on_job():
    """Job.requirement_strictness is stored and accessible."""
    job = _job(requirement_strictness="strict")
    assert job.requirement_strictness == "strict"


def test_requirement_strictness_default_unknown():
    """Default requirement_strictness is 'unknown'."""
    job = _job()
    assert job.requirement_strictness == "unknown"


# ============================================================
# 26. EXPERIENCE RISK ON MATCH
# ============================================================


def test_experience_risk_populated_in_match():
    """score_job populates experience_risk in JobMatch."""
    candidate = _candidate(experience_years=1)
    job = _job(
        experience_years_required=3,
        requirement_strictness="required",
    )

    match = score_job(candidate, job)

    assert match.experience_risk in (
        "low", "medium", "high", "unknown",
    )


def test_experience_risk_default_unknown():
    """When no requirement, risk is 'unknown'."""
    candidate = _candidate(experience_years=5)
    job = _job(experience_years_required=None)

    match = score_job(candidate, job)

    assert match.experience_risk == "unknown"


# ============================================================
# 27. PARTIAL SCORE PROPORTIONAL
# ============================================================


def test_partial_score_is_proportional():
    """Below requirement: score is proportional to years met."""
    job = _job(experience_years_required=4)

    scores = []
    for yrs in [0, 1, 2, 3, 4]:
        cand = _candidate(experience_years=yrs)
        scores.append(calculate_experience_score(cand, job))

    # 0->0, 1->25, 2->50, 3->75, 4->100
    assert scores == [0.0, 25.0, 50.0, 75.0, 100.0]


# ============================================================
# 28. FRACTIONAL EXPERIENCE
# ============================================================


def test_fractional_experience():
    """Fractional years work correctly."""
    candidate = _candidate(experience_years=1.5)
    job = _job(experience_years_required=2)

    score = calculate_experience_score(candidate, job)
    # 1.5/2 * 100 = 75.0
    assert score == 75.0


# ============================================================
# 29. ZERO YEARS vs ZERO REQUIREMENT
# ============================================================


def test_zero_years_vs_zero_requirement():
    """0 vs 0 => 100.0 (requirement met)."""
    candidate = _candidate(experience_years=0)
    job = _job(experience_years_required=0)

    score = calculate_experience_score(candidate, job)
    assert score == 100.0


# ============================================================
# 30. RISK DIFFERS BY STRICTNESS
# ============================================================


def test_risk_varies_by_strictness():
    """Same gap, different strictness => different risk."""
    # Candidate 1 year, requirement 2 years
    risk_strict = classify_experience_risk(1.0, 2.0, "strict")
    risk_required = classify_experience_risk(1.0, 2.0, "required")
    risk_preferred = classify_experience_risk(1.0, 2.0, "preferred")

    # Strict should be higher risk than preferred
    risk_order = {"low": 0, "medium": 1, "high": 2, "unknown": 3}
    assert risk_order[risk_strict] >= risk_order[risk_required]
    assert risk_order[risk_required] >= risk_order[risk_preferred]

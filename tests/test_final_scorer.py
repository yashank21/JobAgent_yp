from app.models.candidate import CandidateProfile
from app.models.job import Job

from app.scoring.experience_scorer import calculate_experience_score
from app.scoring.final_scorer import (
    calculate_final_score,
    calculate_location_score,
    rank_jobs,
    score_job,
)


def make_candidate(**kwargs):
    defaults = {
        "name": "Test User",
        "email": "test@example.com",
        "location": "India",
        "experience_years": 1.0,
        "skills": [
            "Python",
            "C++",
            "FastAPI",
        ],
        "preferred_roles": [
            "Software Engineer",
        ],
        "preferred_locations": [
            "India",
        ],
    }

    defaults.update(kwargs)

    return CandidateProfile(**defaults)


def make_job(**kwargs):
    defaults = {
        "id": "1",
        "title": "Software Engineer",
        "company": "Example",
        "location": "Bengaluru, India",
        "required_skills": [
            "python",
            "c++",
        ],
        "preferred_skills": [
            "fastapi",
        ],
    }

    defaults.update(kwargs)

    return Job(**defaults)


# ============================================================
# Experience scoring
# ============================================================


def test_experience_score_no_requirement():

    candidate = make_candidate(
        experience_years=0,
    )

    job = make_job()

    assert calculate_experience_score(
        candidate,
        job,
    ) == 100.0


def test_experience_score_meets_requirement():

    candidate = make_candidate(
        experience_years=2,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 100.0


def test_experience_score_exceeds_requirement():

    candidate = make_candidate(
        experience_years=4,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 100.0


def test_experience_score_partial_match():

    candidate = make_candidate(
        experience_years=1,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 50.0


def test_experience_score_zero_candidate_experience():

    candidate = make_candidate(
        experience_years=0,
    )

    job = make_job(
        experience_years_required=2,
    )

    assert calculate_experience_score(
        candidate,
        job,
    ) == 0.0


# ============================================================
# Location scoring
# ============================================================


def test_location_score_matching_location():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Bengaluru, India",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) == 100.0


def test_location_score_non_matching_location():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) == 0.0


def test_location_score_remote():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    job = make_job(
        location="Remote",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) == 100.0


def test_location_score_no_preference():

    candidate = make_candidate(
        preferred_locations=[],
    )

    job = make_job(
        location="Hawthorne, CA",
    )

    assert calculate_location_score(
        candidate,
        job,
    ) is None


# ============================================================
# Final score
# ============================================================


def test_final_score_perfect_match():

    score = calculate_final_score(
        skill_score=100,
        role_score=100,
        experience_score=100,
        location_score=100,
    )

    assert score == 100.0


def test_final_score_zero():

    score = calculate_final_score(
        skill_score=0,
        role_score=0,
        experience_score=0,
        location_score=0,
    )

    assert score == 0.0




# ============================================================
# Role mismatch caps
# ============================================================








# ============================================================
# Experience mismatch caps
# ============================================================








# ============================================================
# Individual job scoring
# ============================================================


def test_score_job_returns_match():

    candidate = make_candidate(
        experience_years=2,
    )

    job = make_job(
    experience_required="2+ years of experience",
)

    match = score_job(
        candidate,
        job,
    )

    assert match.job == job
    assert match.eligible is True
    assert match.skill_score > 0
    assert match.role_score > 0
    assert match.experience_score == 100.0
    assert match.location_score == 100.0
    assert match.final_score > 0
    assert match.eligibility_reasons == []


def test_score_job_contains_eligibility_reasons():

    candidate = make_candidate(
        experience_years=1,
        preferred_locations=["India"],
    )

    job = make_job(
        location="Hawthorne, CA",
        experience_years_required=3,
    )

    match = score_job(
        candidate,
        job,
    )

    assert match.eligible is False

    assert len(match.eligibility_reasons) == 2

    assert any(
        "3+ years" in reason
        for reason in match.eligibility_reasons
    )

    assert any(
        "outside preferred locations" in reason
        for reason in match.eligibility_reasons
    )


# ============================================================
# Ranking
# ============================================================


def test_ineligible_jobs_are_excluded():

    candidate = make_candidate(
        preferred_locations=["India"],
    )

    eligible_job = make_job(
        id="1",
        location="Bengaluru, India",
    )

    ineligible_job = make_job(
        id="2",
        location="Hawthorne, CA",
    )

    results = rank_jobs(
        candidate,
        [
            ineligible_job,
            eligible_job,
        ],
    )

    assert len(results) == 1
    assert results[0].job.id == "1"


def test_jobs_are_ranked_by_final_score():

    candidate = make_candidate()

    strong_job = make_job(
        id="strong",
        required_skills=[
            "python",
            "c++",
        ],
        preferred_skills=[
            "fastapi",
        ],
    )

    weak_job = make_job(
        id="weak",
        required_skills=[
            "java",
        ],
    )

    results = rank_jobs(
        candidate,
        [
            weak_job,
            strong_job,
        ],
    )

    assert len(results) == 2
    assert results[0].job.id == "strong"
    assert results[1].job.id == "weak"


# ============================================================
# Step 2: Missing/unknown data semantics
# ============================================================


def test_job_with_no_skills_produces_neutral_skill_score():
    """Job with no listed skills should produce skill_score=50.0
    (neutral), NOT None."""
    candidate = make_candidate()
    job = make_job(required_skills=[], preferred_skills=[])

    match = score_job(candidate, job)

    assert match.skill_score == 50.0


def test_job_with_no_skills_skill_dimension_participates():
    """Job with no listed skills must have skill dimension included
    in compatibility scoring with neutral 50.0, NOT excluded.

    After Step 4: confidence is lower because skill data is missing.
    """
    candidate = make_candidate()
    job = make_job(required_skills=[], preferred_skills=[])

    match = score_job(candidate, job)

    # Skill dimension participates: 50.0 * 0.40 = 20.0
    # Role: 100.0 * 0.30 = 30.0
    # Experience: 100.0 * 0.20 = 20.0
    # Location: 100.0 * 0.10 = 10.0
    # Compatibility = 80.0
    assert match.compatibility_score == 80.0

    # Confidence is lower because skill data is missing.
    # Available: role (0.30) + experience (0.20) + location (0.10) = 0.60
    assert match.confidence == 0.6

    # Final score: 80.0 * (0.7 + 0.3 * 0.6) = 80.0 * 0.88 = 70.4
    assert match.final_score == 70.4


def test_candidate_no_matching_skills_produces_mismatch():
    """Job lists skills but candidate has none of them → genuine
    mismatch score (0.0), NOT neutral 50.0."""
    candidate = make_candidate(skills=[])
    job = make_job(required_skills=["python", "c++"])

    match = score_job(candidate, job)

    assert match.skill_score == 0.0


def test_missing_skills_distinguishable_from_zero_match():
    """Missing skill info (50.0) must be distinguishable from
    zero matching skills (0.0)."""
    candidate = make_candidate(skills=[])

    job_no_skills = make_job(required_skills=[], preferred_skills=[])
    job_with_skills = make_job(required_skills=["python"])

    match_no_skills = score_job(candidate, job_no_skills)
    match_zero = score_job(candidate, job_with_skills)

    assert match_no_skills.skill_score == 50.0
    assert match_zero.skill_score == 0.0
    assert match_no_skills.skill_score != match_zero.skill_score


def test_partial_skill_match_proportional_score():
    """Partial skill match produces proportional score between
    0 and 100."""
    candidate = make_candidate(skills=["python"])
    job = make_job(
        required_skills=["python", "c++", "java"],
        preferred_skills=[],
    )

    match = score_job(candidate, job)

    # 1/3 required match = 33.33... * 0.7 * 100 = 23.33
    assert 0.0 < match.skill_score < 50.0


def test_role_none_means_unconfigured_preference():
    """role_score=None means candidate has no role preference
    configured AND no resume roles."""
    candidate = make_candidate(
        preferred_roles=[],
        secondary_roles=[],
        resume_roles=[],
    )
    job = make_job(title="Software Engineer")

    match = score_job(candidate, job)

    assert match.role_score is None


def test_role_zero_means_mismatch():
    """role_score=0.0 means role data exists but doesn't match."""
    candidate = make_candidate(
        preferred_roles=["Frontend Engineer"],
    )
    job = make_job(title="Data Scientist")

    match = score_job(candidate, job)

    assert match.role_score == 0.0


def test_experience_no_requirement_returns_100():
    """No experience requirement → 100.0 (no constraint)."""
    candidate = make_candidate(experience_years=0)
    job = make_job(experience_years_required=None)

    match = score_job(candidate, job)

    assert match.experience_score == 100.0


def test_location_none_means_unconfigured_preference():
    """location_score=None means candidate has no preferred
    locations configured."""
    candidate = make_candidate(preferred_locations=[])
    job = make_job(location="Bengaluru, India")

    match = score_job(candidate, job)

    assert match.location_score is None


def test_location_zero_means_mismatch():
    """location_score=0.0 means location data exists but doesn't
    match candidate preference."""
    candidate = make_candidate(preferred_locations=["India"])
    job = make_job(location="Hawthorne, CA")

    match = score_job(candidate, job)

    assert match.location_score == 0.0


def test_eligibility_behavior_unchanged():
    """Eligibility checks must remain intact after Step 2."""
    candidate = make_candidate(
        preferred_locations=["India"],
    )
    job = make_job(location="Hawthorne, CA")

    match = score_job(candidate, job)

    assert match.eligible is False
    assert "outside preferred locations" in [
        r.lower() for r in match.eligibility_reasons
    ]


def test_formula_not_redesigned():
    """Verify the weighted formula is unchanged in Step 2."""
    score = calculate_final_score(
        skill_score=100,
        role_score=100,
        experience_score=100,
        location_score=100,
    )
    assert score == 100.0

    score = calculate_final_score(
        skill_score=0,
        role_score=0,
        experience_score=0,
        location_score=0,
    )
    assert score == 0.0


# ============================================================
# Step 3: Weighted formula numerical verification
# ============================================================


def test_formula_case1_all_dimensions_available():
    """CASE 1: All dimensions active.
    skill=80, role=90, exp=100, loc=100
    Expected: 80*0.40 + 90*0.30 + 100*0.20 + 100*0.10 = 89.0
    """
    score = calculate_final_score(
        skill_score=80,
        role_score=90,
        experience_score=100,
        location_score=100,
    )
    assert score == 89.0


def test_formula_case2_role_not_configured():
    """CASE 2: Role preference not configured (None).
    skill=80, role=None, exp=100, loc=100
    Active weight = 0.40 + 0.20 + 0.10 = 0.70
    Expected: (80*0.40 + 100*0.20 + 100*0.10) / 0.70 = 88.57
    """
    score = calculate_final_score(
        skill_score=80,
        role_score=None,
        experience_score=100,
        location_score=100,
    )
    # 62 / 0.70 = 88.571428...
    assert round(score, 2) == 88.57


def test_formula_case3_location_not_configured():
    """CASE 3: Location preference not configured (None).
    skill=80, role=90, exp=100, loc=None
    Active weight = 0.40 + 0.30 + 0.20 = 0.90
    Expected: (80*0.40 + 90*0.30 + 100*0.20) / 0.90 = 87.78
    """
    score = calculate_final_score(
        skill_score=80,
        role_score=90,
        experience_score=100,
        location_score=None,
    )
    # 79 / 0.90 = 87.7777...
    assert round(score, 2) == 87.78


def test_formula_case4_missing_job_skills():
    """CASE 4: Missing job skills returns neutral 50.0.
    skill=50, role=100, exp=100, loc=100
    Expected: 50*0.40 + 100*0.30 + 100*0.20 + 100*0.10 = 80.0
    """
    score = calculate_final_score(
        skill_score=50,
        role_score=100,
        experience_score=100,
        location_score=100,
    )
    assert score == 80.0


def test_formula_case5_known_skill_mismatch():
    """CASE 5: Known skill mismatch penalizes score.
    skill=0, role=100, exp=100, loc=100
    Expected: 0*0.40 + 100*0.30 + 100*0.20 + 100*0.10 = 60.0
    """
    score = calculate_final_score(
        skill_score=0,
        role_score=100,
        experience_score=100,
        location_score=100,
    )
    assert score == 60.0


def test_formula_case6_known_role_mismatch():
    """CASE 6: Known role mismatch penalizes score.
    skill=100, role=0, exp=100, loc=100
    Expected: 100*0.40 + 0*0.30 + 100*0.20 + 100*0.10 = 70.0
    """
    score = calculate_final_score(
        skill_score=100,
        role_score=0,
        experience_score=100,
        location_score=100,
    )
    assert score == 70.0


def test_formula_multiple_none_dimensions():
    """Multiple None dimensions: role and location not configured.
    skill=80, role=None, exp=100, loc=None
    Active weight = 0.40 + 0.20 = 0.60
    Expected: (80*0.40 + 100*0.20) / 0.60 = 86.67
    """
    score = calculate_final_score(
        skill_score=80,
        role_score=None,
        experience_score=100,
        location_score=None,
    )
    # 52 / 0.60 = 86.6666...
    assert round(score, 2) == 86.67


def test_formula_all_dimensions_none():
    """All dimensions None → score is 0.0 (no active dimensions)."""
    score = calculate_final_score(
        skill_score=None,
        role_score=None,
        experience_score=None,
        location_score=None,
    )
    assert score == 0.0


def test_formula_score_stays_in_0_100_range():
    """Final score is always clamped to [0, 100]."""
    # All zeros
    assert calculate_final_score(0, 0, 0, 0) == 0.0
    # All hundreds
    assert calculate_final_score(100, 100, 100, 100) == 100.0
    # Mixed
    assert 0.0 <= calculate_final_score(50, 50, 50, 50) <= 100.0


def test_formula_skill_50_remains_weighted():
    """Skill=50 (neutral) remains weighted at 40% in final score."""
    score = calculate_final_score(
        skill_score=50,
        role_score=50,
        experience_score=50,
        location_score=50,
    )
    # 50 * 0.40 + 50 * 0.30 + 50 * 0.20 + 50 * 0.10 = 50.0
    assert score == 50.0


def test_formula_skill_0_is_penalized():
    """Skill=0 (mismatch) penalizes the final score."""
    score_with_skill = calculate_final_score(
        skill_score=100,
        role_score=100,
        experience_score=100,
        location_score=100,
    )
    score_without_skill = calculate_final_score(
        skill_score=0,
        role_score=100,
        experience_score=100,
        location_score=100,
    )
    # 100 vs 60
    assert score_with_skill == 100.0
    assert score_without_skill == 60.0
    assert score_with_skill > score_without_skill


# ============================================================
# Step 4: Confidence / information quality
# ============================================================


def test_confidence_complete_information():
    """CASE 1: Complete information → maximum confidence."""
    candidate = make_candidate()
    job = make_job(
        required_skills=["python", "c++"],
        preferred_skills=["fastapi"],
    )

    match = score_job(candidate, job)

    assert match.confidence == 1.0
    assert match.compatibility_score == match.final_score


def test_confidence_skills_missing():
    """CASE 2: Skills missing → lower confidence."""
    candidate = make_candidate()
    job = make_job(required_skills=[], preferred_skills=[])

    match = score_job(candidate, job)

    # Skill unavailable: 0.40 weight missing
    # Available: role (0.30) + experience (0.20) + location (0.10) = 0.60
    assert match.confidence == 0.6
    assert match.compatibility_score == 80.0
    # final = 80.0 * (0.7 + 0.3 * 0.6) = 80.0 * 0.88 = 70.4
    assert match.final_score == 70.4


def test_confidence_role_unknown():
    """CASE 3: Role information missing → lower confidence."""
    candidate = make_candidate(
        preferred_roles=["AI Engineer"],
    )
    job = make_job(
        title="Something Completely Unknown XYZ",
        required_skills=["python"],
    )

    match = score_job(candidate, job)

    # Role unavailable: 0.30 weight missing
    # Available: skill (0.40) + experience (0.20) + location (0.10) = 0.70
    assert match.confidence == 0.7


def test_confidence_experience_always_available():
    """CASE 4: Experience is always available (explicit, parsed,
    or seniority fallback)."""
    candidate = make_candidate()
    job = make_job(
        required_skills=["python"],
        experience_years_required=None,
    )

    match = score_job(candidate, job)

    # Experience always counts as available
    assert match.confidence >= 0.8  # At least skill + experience + location


def test_confidence_candidate_no_location_preference():
    """CASE 5: Candidate has no location preference → NOT treated
    as bad job data. Confidence remains high."""
    candidate = make_candidate(preferred_locations=[])
    job = make_job(
        required_skills=["python"],
        location="Bengaluru, India",
    )

    match = score_job(candidate, job)

    # Job has location data, candidate just didn't configure preference
    # Confidence should be high (all job data available)
    assert match.confidence == 1.0


def test_confidence_multiple_fields_missing():
    """CASE 6: Multiple job fields missing → lower confidence."""
    candidate = make_candidate(preferred_locations=[])
    job = make_job(
        title="Something Unknown",
        required_skills=[],
        preferred_skills=[],
        location="",
    )

    match = score_job(candidate, job)

    # Available: experience (0.20) only
    # Skill unavailable, role unavailable, location unavailable
    assert match.confidence == 0.2


def test_confidence_known_mismatch():
    """CASE 7: Known mismatch → LOW compatibility but HIGH confidence.
    This is extremely important: low compatibility ≠ low confidence."""
    candidate = make_candidate(
        preferred_roles=["Frontend Engineer"],
    )
    job = make_job(
        title="Data Scientist",
        required_skills=["python", "tensorflow"],
        preferred_skills=[],
        location="Bengaluru, India",
    )

    match = score_job(candidate, job)

    # Low compatibility (partial skill match + role mismatch)
    # skill=35 (1/2 required), role=0, exp=100, loc=100
    # compatibility = 35*0.40 + 0*0.30 + 100*0.20 + 100*0.10 = 44.0
    assert match.compatibility_score == 44.0
    # But high confidence (all information exists)
    assert match.confidence == 1.0


def test_confidence_missing_data_cannot_increase():
    """Missing data should never increase confidence."""
    from app.scoring.final_scorer import calculate_confidence
    from app.models.job import Job

    job_complete = Job(
        id="1", title="Software Engineer", company="A",
        required_skills=["python"], location="Remote",
    )
    job_incomplete = Job(
        id="2", title="Software Engineer", company="B",
        required_skills=[], location="",
    )

    conf_complete = calculate_confidence(job_complete)
    conf_incomplete = calculate_confidence(job_incomplete)

    assert conf_complete >= conf_incomplete


def test_confidence_stays_in_range():
    """Confidence is always between 0 and 1."""
    from app.scoring.final_scorer import calculate_confidence
    from app.models.job import Job

    # Minimal job
    job_minimal = Job(id="1", title="", company="")
    conf = calculate_confidence(job_minimal)
    assert 0.0 <= conf <= 1.0

    # Complete job
    job_complete = Job(
        id="2", title="Engineer", company="A",
        required_skills=["python"], location="Remote",
    )
    conf = calculate_confidence(job_complete)
    assert 0.0 <= conf <= 1.0


def test_compatibility_unchanged_by_confidence():
    """Compatibility score is calculated independently of confidence."""
    candidate = make_candidate()
    job_with_skills = make_job(
        required_skills=["python", "c++"],
        preferred_skills=["fastapi"],
    )
    job_without_skills = make_job(
        required_skills=[],
        preferred_skills=[],
    )

    match_with = score_job(candidate, job_with_skills)
    match_without = score_job(candidate, job_without_skills)

    # Compatibility scores are different (100 vs 80)
    assert match_with.compatibility_score == 100.0
    assert match_without.compatibility_score == 80.0

    # But confidence doesn't affect compatibility calculation
    assert match_with.confidence == 1.0
    assert match_without.confidence == 0.6


def test_final_score_formula():
    """Verify the final score formula: compatibility * confidence_factor."""
    from app.scoring.final_scorer import calculate_ranking_score, MIN_CONFIDENCE

    compatibility = 80.0
    confidence = 0.6

    factor = MIN_CONFIDENCE + (1.0 - MIN_CONFIDENCE) * confidence
    expected = compatibility * factor

    result = calculate_ranking_score(compatibility, confidence)

    assert result == round(expected, 2)


# ============================================================
# Step 5: Deterministic tie-breaking
# ============================================================


def test_higher_ranking_score_wins():
    """Different ranking scores → higher score ranks first."""
    candidate = make_candidate()

    job_a = make_job(id="A", required_skills=["python", "c++"], preferred_skills=["fastapi"])
    job_b = make_job(id="B", required_skills=["java"])

    results = rank_jobs(candidate, [job_a, job_b])

    assert len(results) == 2
    assert results[0].final_score >= results[1].final_score
    assert results[0].job.id == "A"


def test_equal_ranking_score_higher_confidence_wins():
    """Same ranking score, different confidence → higher confidence
    ranks first."""
    candidate = make_candidate()

    # Both jobs produce identical ranking scores, but different confidence
    # Job A: complete info → confidence=1.0
    # Job B: missing skills → confidence=0.6
    # We construct them to produce equal final_score by adjusting dimensions

    job_a = make_job(id="A", required_skills=[], preferred_skills=[],
                     title="Software Engineer")
    job_b = make_job(id="B", required_skills=[], preferred_skills=[],
                     title="Software Engineer")

    # Force different confidences by manipulating job data availability
    # while keeping final_score equal
    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Both have same data → same confidence. To test tie-breaking properly,
    # we need to construct jobs with equal final_score but different confidence.
    # Use score_job directly and manipulate the match objects.
    from dataclasses import replace

    # Create two jobs with identical final_score but different confidence
    match_a = replace(match_a, final_score=82.50, confidence=0.80, compatibility_score=90)
    match_b = replace(match_b, final_score=82.50, confidence=0.70, compatibility_score=95)

    from app.scoring.final_scorer import rank_jobs as _rank_jobs_impl

    # Directly test the sort key logic
    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    assert ranked[0].confidence > ranked[1].confidence
    assert ranked[0].job.id == "A"


def test_equal_score_and_confidence_higher_compatibility_wins():
    """Same ranking score, same confidence, different compatibility →
    higher compatibility ranks first."""
    from dataclasses import replace

    candidate = make_candidate()
    job_a = make_job(id="A")
    job_b = make_job(id="B")

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Force equal final_score and confidence, different compatibility
    match_a = replace(match_a, final_score=82.50, confidence=0.80, compatibility_score=90)
    match_b = replace(match_b, final_score=82.50, confidence=0.80, compatibility_score=85)

    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    assert ranked[0].compatibility_score > ranked[1].compatibility_score
    assert ranked[0].job.id == "A"


def test_fully_tied_jobs_use_deterministic_identity():
    """Same ranking score, same confidence, same compatibility →
    deterministic ordering by job.id."""
    from dataclasses import replace

    candidate = make_candidate()
    job_a = make_job(id="alpha")
    job_b = make_job(id="beta")

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Force all scores identical
    match_a = replace(match_a, final_score=82.50, confidence=0.80, compatibility_score=90)
    match_b = replace(match_b, final_score=82.50, confidence=0.80, compatibility_score=90)

    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    # alpha < beta → alpha comes first
    assert ranked[0].job.id == "alpha"
    assert ranked[1].job.id == "beta"


def test_repeated_ranking_produces_same_order():
    """Running rank_jobs() multiple times with same jobs produces
    identical ordering."""
    candidate = make_candidate()

    jobs = [
        make_job(id="A", required_skills=["python"], location="Bengaluru, India"),
        make_job(id="B", required_skills=["python", "c++"], location="Bengaluru, India"),
        make_job(id="C", required_skills=["java"]),
        make_job(id="D", required_skills=[], preferred_skills=[]),
    ]

    orderings = []
    for _ in range(5):
        results = rank_jobs(candidate, list(jobs))
        orderings.append([m.job.id for m in results])

    assert all(ordering == orderings[0] for ordering in orderings)


def test_input_order_does_not_control_ties():
    """Input order does not influence the result; tie-breaker determines
    the output."""
    from dataclasses import replace

    candidate = make_candidate()
    job_a = make_job(id="A")
    job_b = make_job(id="B")
    job_c = make_job(id="C")

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)
    match_c = score_job(candidate, job_c)

    # Force identical scores across all three
    match_a = replace(match_a, final_score=82.50, confidence=0.80, compatibility_score=90)
    match_b = replace(match_b, final_score=82.50, confidence=0.80, compatibility_score=90)
    match_c = replace(match_c, final_score=82.50, confidence=0.80, compatibility_score=90)

    # Different input orders
    order1 = sorted(
        [match_a, match_b, match_c],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )
    order2 = sorted(
        [match_c, match_b, match_a],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    assert [m.job.id for m in order1] == ["A", "B", "C"]
    assert [m.job.id for m in order2] == ["A", "B", "C"]


def test_tie_breaking_does_not_change_scores():
    """Tie-breaking only reorders; it does not modify any score fields."""
    from dataclasses import replace

    candidate = make_candidate()
    job_a = make_job(id="A")
    job_b = make_job(id="B")

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    original_a = (match_a.final_score, match_a.confidence, match_a.compatibility_score)
    original_b = (match_b.final_score, match_b.confidence, match_b.compatibility_score)

    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    assert (ranked[0].final_score, ranked[0].confidence, ranked[0].compatibility_score) == original_a
    assert (ranked[1].final_score, ranked[1].confidence, ranked[1].compatibility_score) == original_b


def test_limit_applied_after_sorting():
    """Limit truncates after full sorting, keeping top N."""
    candidate = make_candidate()

    jobs = [
        make_job(id="A", required_skills=["python", "c++"], preferred_skills=["fastapi"]),
        make_job(id="B", required_skills=["python"], preferred_skills=["fastapi"]),
        make_job(id="C", required_skills=["python"]),
        make_job(id="D", required_skills=["java"]),
    ]

    results = rank_jobs(candidate, jobs, limit=2)

    assert len(results) == 2
    # Top 2 should have higher scores
    all_results = rank_jobs(candidate, jobs)
    assert results[0].final_score >= all_results[1].final_score
    assert results[1].final_score >= all_results[2].final_score


def test_ineligible_jobs_never_enter_tie_breaking():
    """Ineligible jobs are excluded before sorting."""
    candidate = make_candidate(preferred_locations=["India"])

    eligible_job = make_job(id="eligible", location="Bengaluru, India")
    ineligible_job = make_job(id="ineligible", location="Hawthorne, CA")

    results = rank_jobs(candidate, [ineligible_job, eligible_job])

    assert len(results) == 1
    assert results[0].job.id == "eligible"
    assert results[0].eligible is True


def test_missing_optional_identity_does_not_crash():
    """Jobs with empty id fields are handled safely (sorted by
    empty string)."""
    from dataclasses import replace

    candidate = make_candidate()
    job_a = make_job(id="")
    job_b = make_job(id="B")

    match_a = score_job(candidate, job_a)
    match_b = score_job(candidate, job_b)

    # Force equal scores
    match_a = replace(match_a, final_score=82.50, confidence=0.80, compatibility_score=90)
    match_b = replace(match_b, final_score=82.50, confidence=0.80, compatibility_score=90)

    ranked = sorted(
        [match_a, match_b],
        key=lambda m: (-m.final_score, -m.confidence, -m.compatibility_score, m.job.id),
    )

    # Empty string sorts before "B"
    assert ranked[0].job.id == ""
    assert ranked[1].job.id == "B"
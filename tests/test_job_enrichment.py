from app.services.job_enrichment import (
    DESCRIPTION_ABSENT,
    DESCRIPTION_PRESENT,
    EXPERIENCE_EXTRACTED,
    EXPERIENCE_NONE_FOUND,
    SKILLS_EXTRACTED,
    SKILLS_NONE_FOUND,
    enrich_job_description,
)
from app.services.experience_parser import parse_experience_years


def test_enrichment_cleans_html_and_extracts_fields():
    result = enrich_job_description(
        "<h2>Requirements</h2><p>Python and 3+ years experience.</p>"
    )

    assert result.description == "Requirements Python and 3+ years experience."
    assert "python" in result.required_skills
    assert result.experience_years_required == 3.0
    assert result.description_status == DESCRIPTION_PRESENT
    assert result.skills_status == SKILLS_EXTRACTED
    assert result.experience_status == EXPERIENCE_EXTRACTED


def test_enrichment_normalizes_aliases():
    result = enrich_job_description(
        "Build retrieval augmented generation systems with ML and LLMs."
    )

    assert "retrieval-augmented generation" in result.required_skills
    assert "machine learning" in result.required_skills
    assert "large language models" in result.required_skills


def test_enrichment_extracts_lower_bound_of_experience_range():
    result = enrich_job_description("3-5 years of experience with Python.")

    assert result.experience_years_required == 3.0
    assert result.experience_required == "3-5 years of experience with Python."


def test_enrichment_marks_missing_description_as_not_attempted():
    result = enrich_job_description("")

    assert result.description_status == DESCRIPTION_ABSENT
    assert result.skills_status == "not_attempted"
    assert result.experience_status == "not_attempted"


def test_enrichment_distinguishes_no_known_information():
    result = enrich_job_description("Work with proprietary systems and teams.")

    assert result.description_status == DESCRIPTION_PRESENT
    assert result.skills_status == SKILLS_NONE_FOUND
    assert result.experience_status == EXPERIENCE_NONE_FOUND


def test_enrichment_falls_back_to_full_description_without_known_sections():
    result = enrich_job_description(
        "What you will do: Build services. Python experience required."
    )

    assert "python" in result.required_skills
    assert result.experience_years_required is None
    assert result.experience_status == EXPERIENCE_NONE_FOUND


def test_enrichment_falls_back_when_prose_looks_like_a_section():
    result = enrich_job_description(
        "Our ideal candidate will have Qualifications and 2+ years of experience."
    )

    assert result.experience_years_required == 2.0


def test_enrichment_does_not_match_ai_inside_words():
    result = enrich_job_description("Maintain logging and governance systems.")

    assert "artificial intelligence" not in result.required_skills


def test_experience_parser_handles_observed_unicode_and_possessive_forms():
    assert parse_experience_years("1–2 years of experience") == 1.0
    assert parse_experience_years("3 years' experience") == 3.0


def test_section_experience_is_preferred_over_full_description():
    result = enrich_job_description(
        "Requirements: 3+ years of experience."
    )

    assert result.experience_years_required == 3.0


def test_experience_remains_unknown_without_supported_text():
    result = enrich_job_description(
        "Requirements: Python and strong communication skills."
    )

    assert result.experience_years_required is None

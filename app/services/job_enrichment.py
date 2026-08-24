"""Shared job-description cleaning and extraction."""

from dataclasses import dataclass

from app.services.experience_parser import parse_experience_years
from app.services.job_parser import extract_section
from app.services.skill_extractor import extract_skills
from app.services.skill_normalizer import normalize_skills
from app.services.text_cleaner import clean_html


DESCRIPTION_PRESENT = "present"
DESCRIPTION_ABSENT = "absent"
DESCRIPTION_RETRIEVAL_FAILED = "retrieval_failed"
DESCRIPTION_NOT_REQUESTED = "not_requested"

SKILLS_EXTRACTED = "extracted"
SKILLS_NONE_FOUND = "none_found"
SKILLS_NOT_ATTEMPTED = "not_attempted"

EXPERIENCE_EXTRACTED = "extracted"
EXPERIENCE_NONE_FOUND = "none_found"
EXPERIENCE_NOT_ATTEMPTED = "not_attempted"


@dataclass
class EnrichedJobDescription:
    description: str = ""
    experience_required: str = ""
    experience_years_required: float | None = None
    seniority: str = "unknown"
    role_family: str = ""
    job_type: str | None = None
    required_skills: list[str] | None = None
    preferred_skills: list[str] | None = None
    description_status: str = DESCRIPTION_ABSENT
    skills_status: str = SKILLS_NOT_ATTEMPTED
    experience_status: str = EXPERIENCE_NOT_ATTEMPTED
    gemini_confidence: float = 0.0


def description_from_response(response: object) -> str:
    """Extract a textual JD from common HTML or JSON responses."""
    if isinstance(response, str):
        return response

    if not isinstance(response, dict):
        return ""

    job_info = response.get("jobPostingInfo")
    if isinstance(job_info, dict):
        description = job_info.get("jobDescription")
        if isinstance(description, str):
            return description

    for key in ("description", "descriptionPlain", "jobDescription"):
        description = response.get(key)
        if isinstance(description, str):
            return description

    return ""


REQUIRED_SECTIONS = [
    "BASIC QUALIFICATIONS",
    "BASIC QUALIFICATION",
    "REQUIRED QUALIFICATIONS",
    "REQUIRED QUALIFICATION",
    "REQUIRED SKILLS",
    "REQUIRED SKILLS AND EXPERIENCE",
    "REQUIRED SKILLS & EXPERIENCE",
    "REQUIRED EXPERIENCE",
    "QUALIFICATIONS",
    "QUALIFICATION",
    "YOUR EXPERTISE",
    "YOUR QUALIFICATIONS",
    "WHAT YOU BRING",
    "WHAT YOU'LL BRING",
    "WHAT YOU WILL BRING",
    "MINIMUM QUALIFICATIONS",
    "MINIMUM REQUIREMENTS",
]

PREFERRED_SECTIONS = [
    "PREFERRED SKILLS",
    "PREFERRED QUALIFICATIONS",
    "PREFERRED EXPERIENCE",
    "PREFERRED REQUIREMENTS",
    "NICE TO HAVE",
    "NICE-TO-HAVE",
    "BONUS QUALIFICATIONS",
    "BONUS SKILLS",
]

SECTION_BOUNDARIES = [
    *REQUIRED_SECTIONS,
    *PREFERRED_SECTIONS,
    "ADDITIONAL REQUIREMENTS",
    "ADDITIONAL QUALIFICATIONS",
    "COMPENSATION AND BENEFITS",
    "ITAR REQUIREMENTS",
    "WHAT YOU'LL DO",
    "WHAT YOU WILL DO",
    "WHAT WE'LL DO",
    "WHAT WE WILL DO",
    "RESPONSIBILITIES",
    "RESPONSIBILITY",
    "ABOUT THE ROLE",
    "ABOUT YOU",
    "THE ROLE",
    "RESPONSIBILITIES AND DUTIES",
    "DUTIES",
]


def _section_text(
    description: str,
    sections: list[str],
) -> str:
    for section in sections:
        text = extract_section(
            description,
            section,
            [
                item
                for item in SECTION_BOUNDARIES
                if item != section
            ],
        )

        if text:
            return text

    return ""


def _merge_skills(
    primary: list[str],
    secondary: list[str],
) -> list[str]:
    """
    Merge skills while treating the primary source as authoritative.

    Both collections are normalized before merging.
    """

    normalized = set()

    for skill in primary + secondary:
        if not skill:
            continue

        normalized.add(
            skill.strip().lower()
        )

    return sorted(normalized)


def _try_gemini_enrichment(
    *,
    title: str,
    description: str,
) -> dict:
    """
    Run Gemini enrichment safely.

    Gemini is optional. Any failure returns an empty result
    and must never break job collection.
    """

    try:
        from app.services.gemini_enricher import (
            GeminiJobEnricher,
        )

        enricher = GeminiJobEnricher()

        return enricher.analyze(
            title=title,
            description=description,
        )

    except Exception as exc:
        print(
            f"[Gemini] enrichment failed: "
            f"{type(exc).__name__}: {exc}"
        )

        return {
            "required_skills": [],
            "preferred_skills": [],
            "experience_years": None,
            "seniority": None,
            "role_family": "Other",
            "job_type": None,
            "confidence": 0.0,
        }


def enrich_job_description(
    description: str | None,
    *,
    title: str = "",
    retrieval_status: str | None = None,
    use_gemini: bool = False,
) -> EnrichedJobDescription:
    """
    Clean a JD and extract structured fields.

    Pipeline:

        HTML cleaning
            ↓
        deterministic extraction
            ↓
        Gemini semantic enrichment
            ↓
        merge + normalize
    """

    if not description or not description.strip():
        return EnrichedJobDescription(
            required_skills=[],
            preferred_skills=[],
            description_status=(
                retrieval_status
                or DESCRIPTION_ABSENT
            ),
            skills_status=SKILLS_NOT_ATTEMPTED,
            experience_status=EXPERIENCE_NOT_ATTEMPTED,
        )

    cleaned = clean_html(description)

    if not cleaned:
        return EnrichedJobDescription(
            required_skills=[],
            preferred_skills=[],
            description_status=DESCRIPTION_ABSENT,
            skills_status=SKILLS_NOT_ATTEMPTED,
            experience_status=EXPERIENCE_NOT_ATTEMPTED,
        )

    # -------------------------------------------------
    # 1. Deterministic extraction
    # -------------------------------------------------

    required_text = _section_text(
        cleaned,
        REQUIRED_SECTIONS,
    )

    preferred_text = _section_text(
        cleaned,
        PREFERRED_SECTIONS,
    )

    section_skills = extract_skills(
        required_text
    )

    section_experience = parse_experience_years(
        required_text
    )

    use_required_section = bool(
        section_skills
        or section_experience is not None
    )

    experience_years = (
        section_experience
        if section_experience is not None
        else parse_experience_years(cleaned)
    )

    experience_text = (
        required_text
        if section_experience is not None
        else (
            cleaned
            if experience_years is not None
            else ""
        )
    )

    rule_required_skills = list(
    normalize_skills(
        section_skills
    )
    )

    rule_preferred_skills = (
        list(
            normalize_skills(
                extract_skills(
                    preferred_text
                )
            )
        )
        if preferred_text
        else []
    )

    # -------------------------------------------------
    # 2. Gemini semantic enrichment
    # -------------------------------------------------

    gemini_result = {}

    if use_gemini:
        gemini_result = _try_gemini_enrichment(
            title=title,
            description=cleaned,
        )

    gemini_required = list(
        normalize_skills(
            gemini_result.get(
                "required_skills",
                [],
            )
        )
    )

    gemini_preferred = list(
        normalize_skills(
            gemini_result.get(
                "preferred_skills",
                [],
            )
        )
    )

    # -------------------------------------------------
    # 3. Merge skills
    # -------------------------------------------------

    gemini_confidence = float(
        gemini_result.get(
            "confidence",
            0.0,
        )
        or 0.0
    )

    gemini_has_semantic_result = any(
    [
        gemini_result.get("required_skills"),
        gemini_result.get("preferred_skills"),
        gemini_result.get("experience_years") is not None,
        gemini_result.get("seniority"),
        gemini_result.get("role_family"),
        gemini_result.get("job_type"),
    ]
    )

    # If Gemini produced a reasonably confident semantic result,
    # trust its required/preferred classification.
    #
    # Deterministic extraction is only used as a supplement when:
    #   1. Gemini failed/returned nothing, OR
    #   2. there is an explicit REQUIRED section in the JD.
    #
    # This prevents a word such as "AWS" appearing anywhere in the JD
    # from incorrectly becoming a required skill.

    if (
        use_gemini
        and gemini_has_semantic_result
        and gemini_confidence >= 0.60
    ):
        if use_required_section:
            required_skills = _merge_skills(
                gemini_required,
                rule_required_skills,
            )
        else:
            required_skills = gemini_required

        preferred_skills = _merge_skills(
            gemini_preferred,
            rule_preferred_skills,
        )

    else:
        required_skills = _merge_skills(
            rule_required_skills,
            gemini_required,
        )

        preferred_skills = _merge_skills(
            rule_preferred_skills,
            gemini_preferred,
        )

    # A skill cannot simultaneously be required and preferred.
    preferred_skills = [
        skill
        for skill in preferred_skills
        if skill not in required_skills
    ]

    # -------------------------------------------------
    # 4. Experience
    # -------------------------------------------------

    gemini_experience = gemini_result.get(
        "experience_years"
    )

    if experience_years is None:
        experience_years = gemini_experience

        if gemini_experience is not None:
            experience_text = cleaned

    # -------------------------------------------------
    # 5. Semantic metadata
    # -------------------------------------------------

    seniority = gemini_result.get(
        "seniority"
    ) or "unknown"

    role_family = gemini_result.get(
        "role_family"
    ) or ""

    job_type = gemini_result.get(
        "job_type"
    )

    confidence = float(
        gemini_result.get(
            "confidence",
            0.0,
        )
        or 0.0
    )

    return EnrichedJobDescription(
        description=cleaned,
        experience_required=(
            experience_text
            if experience_years is not None
            else ""
        ),
        experience_years_required=experience_years,
        seniority=seniority,
        role_family=role_family,
        job_type=job_type,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        description_status=DESCRIPTION_PRESENT,
        skills_status=(
            SKILLS_EXTRACTED
            if required_skills
            or preferred_skills
            else SKILLS_NONE_FOUND
        ),
        experience_status=(
            EXPERIENCE_EXTRACTED
            if experience_years is not None
            else EXPERIENCE_NONE_FOUND
        ),
        gemini_confidence=confidence,
    )
"""Shared job-description cleaning and extraction."""

from dataclasses import dataclass

from app.services.experience_parser import parse_experience_years
from app.services.groq_enricher import GroqJobEnricher
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

    # Current generic AI confidence.
    ai_confidence: float = 0.0


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

    for key in (
        "description",
        "descriptionPlain",
        "jobDescription",
    ):
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
    Merge skills while normalizing casing and whitespace.
    """

    normalized = set()

    for skill in primary + secondary:
        if not skill:
            continue

        normalized.add(
            skill.strip().lower()
        )

    return sorted(normalized)


def _try_ai_enrichment(
    *,
    title: str,
    description: str,
) -> dict:
    """
    Run Groq enrichment safely.

    AI enrichment is optional. Any failure returns an empty
    result and must never break job collection.
    """

    try:
        enricher = GroqJobEnricher()

        return enricher.analyze(
            title=title,
            description=description,
        )

    except Exception as exc:
        print(
            f"[Groq] enrichment failed: "
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
    use_ai: bool = False,
) -> EnrichedJobDescription:
    """
    Clean a JD and extract structured fields.

    Pipeline:

        HTML cleaning
            ↓
        deterministic extraction
            ↓
        Groq semantic enrichment
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
    required_text or cleaned
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
    # 2. Groq semantic enrichment
    # -------------------------------------------------

    ai_result = {}

    if use_ai:
        ai_result = _try_ai_enrichment(
            title=title,
            description=cleaned,
        )

    groq_required = list(
        normalize_skills(
            ai_result.get(
                "required_skills",
                [],
            )
        )
    )

    groq_preferred = list(
        normalize_skills(
            ai_result.get(
                "preferred_skills",
                [],
            )
        )
    )

    groq_confidence = float(
        ai_result.get(
            "confidence",
            0.0,
        )
        or 0.0
    )

    groq_has_semantic_result = any(
        [
            ai_result.get("required_skills"),
            ai_result.get("preferred_skills"),
            ai_result.get("experience_years") is not None,
            ai_result.get("seniority"),
            ai_result.get("role_family"),
            ai_result.get("job_type"),
        ]
    )

    # -------------------------------------------------
    # 3. Merge skills
    # -------------------------------------------------

    # Deterministic extraction is the primary source.
    # Groq only supplements it.

    required_skills = _merge_skills(
            rule_required_skills,
            groq_required,
        )

    preferred_skills = _merge_skills(
            rule_preferred_skills,
            groq_preferred,
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

    groq_experience = ai_result.get(
        "experience_years"
    )

    if experience_years is None:
        experience_years = groq_experience

        if groq_experience is not None:
            experience_text = cleaned

    # -------------------------------------------------
    # 5. Semantic metadata
    # -------------------------------------------------

    seniority = (
        ai_result.get("seniority")
        or "unknown"
    )

    role_family = (
        ai_result.get("role_family")
        or ""
    )

    job_type = ai_result.get(
        "job_type"
    )

    confidence = groq_confidence

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


        # Compatibility with the existing Job model/scoring.
        ai_confidence=confidence,
    )

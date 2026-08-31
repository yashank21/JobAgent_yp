"""
Skill extraction utilities.

Extracts known technical skills from job-description text.

The extractor is intentionally deterministic and lightweight.
Semantic interpretation (required vs preferred vs merely mentioned)
will be handled later by the semantic analysis layer.
"""

import re


# ---------------------------------------------------------------------------
# Canonical skill aliases
# ---------------------------------------------------------------------------
#
# Multiple ways of writing the same skill are normalized to one canonical
# representation.
#
# Example:
#   golang       -> go
#   nodejs       -> node.js
#   nextjs       -> next.js
#   sklearn      -> scikit-learn
#   apache spark -> spark
#

SKILL_ALIASES = {
    # Programming languages
    "golang": "go",

    # Databases / storage
    "sql server": "sql server",

    # AI / ML
    "sklearn": "scikit-learn",
    "hugging face": "hugging face",
    "llms": "llm",

    "retrieval augmented generation": "retrieval-augmented generation",

    # Web
    "nextjs": "next.js",
    "nodejs": "node.js",
    "rest api": "rest",
    
    # Data
    "apache spark": "spark",

    # DevOps
    "gitlab ci": "gitlab ci",
}


# ---------------------------------------------------------------------------
# Known technical skills
# ---------------------------------------------------------------------------

TECH_SKILLS = {
    # ----------------------------------------
    # Programming languages
    # ----------------------------------------

    "python",
    "c++",
    "c#",
    "java",
    "javascript",
    "typescript",
    "go",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",
    "rust",

    # ----------------------------------------
    # Databases / storage / query
    # ----------------------------------------

    "sql",
    "sql server",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "elasticsearch",
    "dynamodb",
    "cassandra",
    "sqlite",
    "oracle",

    # ----------------------------------------
    # AI / ML
    # ----------------------------------------

    "ai",
    "ml",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "natural language processing",
    "nlp",
    "computer vision",
    "generative ai",
    "rag",
    "retrieval-augmented generation",
    "llm",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "hugging face",
    "transformers",
    "langchain",
    "langgraph",

    # ----------------------------------------
    # Backend / Web
    # ----------------------------------------

    "fastapi",
    "flask",
    "django",
    "sqlalchemy",
    "react",
    "three.js",
    "next.js",
    "node.js",
    "express",
    "graphql",
    "rest",
    "microservices",

    # ----------------------------------------
    # Distributed systems / messaging
    # ----------------------------------------

    "kafka",
    "rabbitmq",
    "grpc",
    "distributed systems",

    # ----------------------------------------
    # Cloud / infrastructure
    # ----------------------------------------

    "linux",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "hpc",
    "terraform",
    "ansible",

    # ----------------------------------------
    # DevOps / CI/CD
    # ----------------------------------------

    "ci/cd",
    "jenkins",
    "github actions",
    "gitlab ci",
    "git",
    "github",

    # ----------------------------------------
    # Frontend
    # ----------------------------------------

    "html",
    "css",
    "tailwind",
    "tailwind css",

    # ----------------------------------------
    # Data / analytics
    # ----------------------------------------

    "pandas",
    "numpy",
    "spark",
    "airflow",
    "databricks",

    # ----------------------------------------
    # Simulation / engineering
    # ----------------------------------------

    "openfoam",
    "ansys fluent",
    "comsol multiphysics",
    "ansys meshing",
    "snappyhexmesh",
    "paraview",
    "tecplot",
    "nx",
}


# ---------------------------------------------------------------------------
# Generic / ambiguous terms
# ---------------------------------------------------------------------------
#
# These are real technical concepts but are too ambiguous to safely extract
# from arbitrary job-description prose using a simple keyword matcher.
#
# They will eventually be handled by semantic analysis.
#

AMBIGUOUS_SKILLS = {
    "ai",
    "ml",
    "api",
    "rest",
    "rag",
    "nlp",
    "llm",
}


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize_text(text: str) -> str:
    """Normalize text for matching."""

    text = text.lower()

    # Normalize common dash variants.
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    # Normalize repeated whitespace.
    text = re.sub(r"\s+", " ", text)

    return text


def _canonical_skill(skill: str) -> str:
    """Return canonical representation of a skill."""

    skill_lower = skill.lower().strip()

    return SKILL_ALIASES.get(
        skill_lower,
        skill_lower,
    )


def _skill_pattern(skill: str) -> re.Pattern:
    escaped = re.escape(skill.lower())

    return re.compile(
        rf"(?<![a-zA-Z0-9]){escaped}(?![a-zA-Z0-9])",
        re.IGNORECASE,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_skills(
    text: str,
    skills: set[str] | None = None,
) -> list[str]:
    """
    Extract known technical skills from text.

    Matching is case-insensitive.

    Skills are returned using canonical names and in deterministic order.

    Important:
        This function only answers:
            "Is this skill mentioned?"

        It does NOT claim that a skill is required.

        Required/preferred/mentioned classification belongs to the
        higher-level job parsing / semantic analysis layer.
    """

    if not text:
        return []

    normalized_text = _normalize_text(text)

    candidate_skills = skills or TECH_SKILLS

    found: set[str] = set()

    # Match longer phrases first so that:
    #
    #   machine learning
    #
    # is considered before:
    #
    #   ml
    #
    # and:
    #
    #   apache spark
    #
    # is normalized to:
    #
    #   spark
    #
        # Search both canonical skills and their known aliases.
    #
    # Aliases are surface forms only. They are always converted to their
    # canonical representation before being returned.
    searchable_skills = set(candidate_skills)

    for alias, canonical in SKILL_ALIASES.items():
        if canonical in candidate_skills:
            searchable_skills.add(alias)

    ordered_skills = sorted(
        searchable_skills,
        key=len,
        reverse=True,
    )

    for skill in ordered_skills:
        canonical = _canonical_skill(skill)

        pattern = _skill_pattern(skill)

        if pattern.search(normalized_text):
            found.add(canonical)

    # ------------------------------------------------------------------
    # Remove redundant aliases / generic duplicates.
    # ------------------------------------------------------------------

    # If a specific representation exists, don't separately return its
    # shorter alias.
    #
    # Example:
    #
    #   retrieval-augmented generation
    #   rag
    #
    # should not become two independent skills.
    #

    if "retrieval-augmented generation" in found:
        found.discard("rag")

    if "llm" in found:
        # "llm" is retained as the canonical concept.
        pass

    # Return deterministic output.
    return sorted(found)


def extract_skill_details(
    text: str,
    skills: set[str] | None = None,
) -> dict[str, list[str]]:
    """
    Extract skills with a basic confidence classification.

    This is intentionally conservative.

    Strong skills:
        Explicit, unambiguous technical skills.

    Ambiguous skills:
        Short/common terms such as AI, ML, API, REST, etc.

    Semantic classification will later be handled by AI enrichment layer.
    """

    extracted = extract_skills(
        text,
        skills=skills,
    )

    strong = []
    ambiguous = []

    for skill in extracted:
        if skill in AMBIGUOUS_SKILLS:
            ambiguous.append(skill)
        else:
            strong.append(skill)

    return {
        "strong": strong,
        "ambiguous": ambiguous,
    }

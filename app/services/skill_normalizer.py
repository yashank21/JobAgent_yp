"""
Skill normalization utilities.

Converts equivalent skill names into canonical names
so candidate and job skills can be compared correctly.
"""

import re


SKILL_ALIASES = {
    # Generative AI / LLM
    "rag": "retrieval-augmented generation",
    "retrieval augmented generation": "retrieval-augmented generation",
    "retrieval-augmented generation": "retrieval-augmented generation",

    "llm": "large language models",
    "llms": "large language models",
    "large language model": "large language models",
    "large language models": "large language models",

    # Machine learning
    "ml": "machine learning",
    "machine learning": "machine learning",

    # Artificial intelligence
    "ai": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",

    # NLP
    "nlp": "natural language processing",
    "natural language processing": "natural language processing",

    # Computer vision
    "cv": "computer vision",
    "computer vision": "computer vision",

    # Python
    "python": "python",

    # C++
    "c++": "c++",
    "c ++": "c++",

    # JavaScript
    "js": "javascript",
    "javascript": "javascript",

    # TypeScript
    "ts": "typescript",
    "typescript": "typescript",

    # SQL
    "sql": "sql",

    # Scikit-learn
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "scikit-learn": "scikit-learn",

    # PyTorch
    "pytorch": "pytorch",

    # TensorFlow
    "tensorflow": "tensorflow",

    # PostgreSQL
    "postgres": "postgresql",
    "postgresql": "postgresql",

    # MySQL
    "mysql": "mysql",

    # FastAPI
    "fast api": "fastapi",
    "fastapi": "fastapi",

    # React
    "react.js": "react",
    "reactjs": "react",
    "react": "react",

    # Git
    "git": "git",
    "github": "github",
}


def _clean_skill(skill: str) -> str:
    """Clean formatting without changing the skill meaning."""

    skill = skill.strip().lower()

    skill = re.sub(r"\s+", " ", skill)

    return skill


def normalize_skill(skill: str) -> str:
    """
    Convert a skill to its canonical representation.

    Unknown skills are preserved after basic normalization.
    """

    if not skill:
        return ""

    cleaned = _clean_skill(skill)

    return SKILL_ALIASES.get(
        cleaned,
        cleaned,
    )


def normalize_skills(
    skills: list[str],
) -> set[str]:
    """
    Normalize a collection of skills.

    Returns a set so duplicate aliases collapse
    into one canonical skill.
    """

    normalized = {
        normalize_skill(skill)
        for skill in skills
    }

    return {
        skill
        for skill in normalized
        if skill
    }
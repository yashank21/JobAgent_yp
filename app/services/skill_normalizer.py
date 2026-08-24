"""
Skill normalization utilities.

Converts equivalent skill names into canonical names
so candidate and job skills can be compared correctly.
"""

import re


SKILL_ALIASES = {
    # Artificial intelligence
    "ai": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",
    "artificial intelligence (ai)": "artificial intelligence",

    # Generative AI / LLM
    "rag": "retrieval-augmented generation",
    "retrieval augmented generation": "retrieval-augmented generation",
    "retrieval-augmented generation": "retrieval-augmented generation",
    "retrieval augmented generation (rag)": "retrieval-augmented generation",
    "retrieval-augmented generation (rag)": "retrieval-augmented generation",
    "rag (retrieval-augmented generation)": "retrieval-augmented generation",

    "llm": "large language models",
    "llms": "large language models",
    "large language model": "large language models",
    "large language models": "large language models",
    "large language models (llms)": "large language models",
    "large language model (llm)": "large language models",

    "genai": "generative ai",
    "gen ai": "generative ai",
    "generative ai": "generative ai",
    "generative artificial intelligence": "generative ai",

    # Large language models
    "llm": "large language models",
    "llms": "large language models",
    "large language model": "large language models",
    "large language models": "large language models",
    "large language models (llms)": "large language models",
    "large language model (llm)": "large language models",

    # Machine learning
    "ml": "machine learning",
    "machine learning": "machine learning",

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
    
    # AWS
    "amazon web services": "aws",
    "aws": "aws",

    # Apache Spark
    "apache spark": "spark",
    "spark": "spark",

    # Node.js
    "node": "node.js",
    "node.js": "node.js",
    "nodejs": "node.js",

    # Next.js
    "next": "next.js",
    "next.js": "next.js",
    "nextjs": "next.js",

    # Hugging Face
    "huggingface": "hugging face",
    "hugging face": "hugging face",

    # C#
    "c sharp": "c#",
    "c#": "c#",
    # Cloud platforms
    "google cloud platform": "gcp",
    "gcp": "gcp",

    "amazon web services": "aws",
    "aws": "aws",

    "microsoft azure": "azure",
    "azure": "azure",

    # Kafka
    "apache kafka": "kafka",
    "kafka": "kafka",

    # Business intelligence
    "business intelligence": "business intelligence",
    "business intelligence (bi)": "business intelligence",

    # APIs
    "rest api": "rest apis",
    "rest apis": "rest apis",
    "restful api": "rest apis",
    "restful apis": "rest apis",

    # PySpark
    "pyspark": "pyspark",
    "apache spark": "spark",
    "spark": "spark",
    
    # MLOps
    "mlops": "mlops",
    "ml ops": "mlops",
    "machine learning operations": "mlops",

    # Kubernetes
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",

    # CI/CD
    "ci/cd": "ci/cd",
    "ci cd": "ci/cd",
    "continuous integration": "ci/cd",
    "continuous delivery": "ci/cd",
    "continuous deployment": "ci/cd",
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
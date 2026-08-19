"""
Skill extraction utilities.

Extracts known technical skills from job-description text.
"""

import re


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
    "golang",
    "rust",
    "ruby",
    "php",
    "swift",
    "kotlin",
    "scala",

    # ----------------------------------------
    # Databases / storage / query
    # ----------------------------------------

    "sql",
    "postgresql",
    "mysql",
    "sql server",
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
    "llm",
    "llms",
    "pytorch",
    "tensorflow",
    "scikit-learn",
    "sklearn",
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
"nextjs",
"node.js",
"nodejs",
"express",
"graphql",
"rest",
"rest api",
"api",
"microservices",

    # ----------------------------------------
    # Distributed systems / messaging
    # ----------------------------------------

    "kafka",
    "rabbitmq",
    "grpc",
    "redis",
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
    "apache spark",
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
    "visit",
    "tecplot",
    "nx",
}


def extract_skills(
    text: str,
    skills: set[str] | None = None,
) -> list[str]:
    """
    Extract known technical skills from text.

    Matching is case-insensitive.

    Returns skills in a deterministic order.
    """

    if not text:
        return []

    skills = skills or TECH_SKILLS

    text_lower = text.lower()

    found = []

    for skill in sorted(
        skills,
        key=len,
        reverse=True,
    ):
        pattern = (
            rf"(?<!\w)"
            rf"{re.escape(skill.lower())}"
            rf"(?!\w)"
        )

        if re.search(
            pattern,
            text_lower,
        ):
            found.append(skill)

    return found
"""
Skill extraction utilities.

Extracts known technical skills from job-description text.
"""

import re


TECH_SKILLS = {
    # Programming languages
    "python",
    "c++",
    "java",
    "javascript",
    "typescript",
    "go",
    "rust",

    # Databases / query
    "sql",
    "postgresql",
    "mysql",
    "sql server",
    "mongodb",

    # AI / ML
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "pytorch",
    "tensorflow",

    # Backend / web
    "fastapi",
    "flask",
    "django",
    "sqlalchemy",
    "react",
    "three.js",

    # Infrastructure / systems
    "linux",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "hpc",

    # Simulation / engineering
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
        pattern = rf"(?<!\w){re.escape(skill.lower())}(?!\w)"

        if re.search(pattern, text_lower):
            found.append(skill)

    return found
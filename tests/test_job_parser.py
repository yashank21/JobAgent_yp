from app.services.job_parser import extract_section


DESCRIPTION = """
SpaceX is developing advanced software.

RESPONSIBILITIES:
Build simulation software.
Develop machine learning solutions.

BASIC QUALIFICATIONS:
Bachelor's degree in computer science.
2+ years of software development experience in C++ or Python.

PREFERRED SKILLS:
Experience with machine learning.
Strong Linux experience.
Knowledge of HPC environments.

ADDITIONAL REQUIREMENTS:
Ability to travel.
Ability to work extended hours.

COMPENSATION AND BENEFITS:
Pay Range: $125,000 - $160,000.
"""


def test_extract_basic_qualifications():

    result = extract_section(
        DESCRIPTION,
        "BASIC QUALIFICATIONS",
        [
            "PREFERRED SKILLS",
            "ADDITIONAL REQUIREMENTS",
            "COMPENSATION AND BENEFITS",
        ],
    )

    assert "Bachelor's degree" in result
    assert "2+ years" in result
    assert "PREFERRED SKILLS" not in result


def test_extract_preferred_skills():

    result = extract_section(
        DESCRIPTION,
        "PREFERRED SKILLS",
        [
            "ADDITIONAL REQUIREMENTS",
            "COMPENSATION AND BENEFITS",
        ],
    )

    assert "machine learning" in result
    assert "Linux" in result
    assert "HPC" in result
    assert "ADDITIONAL REQUIREMENTS" not in result


def test_missing_section():

    result = extract_section(
        DESCRIPTION,
        "EDUCATION",
        [
            "PREFERRED SKILLS",
        ],
    )

    assert result == ""
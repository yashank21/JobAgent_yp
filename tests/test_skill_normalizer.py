from app.services.skill_normalizer import (
    normalize_skill,
    normalize_skills,
)


def test_normalize_rag():
    assert (
        normalize_skill("RAG")
        == "retrieval-augmented generation"
    )


def test_normalize_llm():
    assert (
        normalize_skill("LLM")
        == "large language models"
    )


def test_normalize_nlp():
    assert (
        normalize_skill("NLP")
        == "natural language processing"
    )


def test_normalize_machine_learning():
    assert (
        normalize_skill("ML")
        == "machine learning"
    )


def test_normalize_cplusplus():
    assert (
        normalize_skill("C ++")
        == "c++"
    )


def test_normalize_react():
    assert (
        normalize_skill("React.js")
        == "react"
    )


def test_normalize_unknown_skill():
    assert (
        normalize_skill("OpenFOAM")
        == "openfoam"
    )


def test_normalize_whitespace():
    assert (
        normalize_skill("  Python  ")
        == "python"
    )


def test_aliases_collapse():
    skills = normalize_skills(
        [
            "RAG",
            "Retrieval-Augmented Generation",
            "rag",
        ]
    )

    assert skills == {
        "retrieval-augmented generation"
    }


def test_multiple_skills():
    skills = normalize_skills(
        [
            "Python",
            "C++",
            "LLM",
            "NLP",
            "React.js",
        ]
    )

    assert skills == {
        "python",
        "c++",
        "large language models",
        "natural language processing",
        "react",
    }


def test_empty_skill():
    assert normalize_skill("") == ""


def test_empty_skills():
    assert normalize_skills([]) == set()
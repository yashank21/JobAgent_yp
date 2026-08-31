from app.models.candidate import CandidateProfile
from app.services.resume_classifier import classify_resume
from app.services.candidate_profile_builder import build_candidate_profile


def test_resume_classification_produces_candidate_signals():
    resume_text = """
    AI/ML Engineer with 1 year of experience.

    Software Engineering Intern at Example Corp.

    Skills:
    Python, C++, SQL, PyTorch, TensorFlow, LangChain,
    Machine Learning, Deep Learning, RAG, NLP.

    Education:
    MTech in Information Technology.
    """

    classification = classify_resume(
        resume_text
    )

    assert classification.skills
    assert classification.role_titles
    assert classification.role_families

    assert classification.experience_years == 1.0
    assert classification.career_level == "intern"


def test_resume_does_not_overwrite_user_preferences():
    base_profile = CandidateProfile(
        preferred_roles=[
            "AI Engineer",
            "ML Engineer",
            "Machine Learning Engineer",
            "LLM Engineer",
            "Applied Scientist",
            "Research Engineer",
        ],
        preferred_locations=[
            "India",
            "Bengaluru",
            "Hyderabad",
            "Pune",
            "Remote",
        ],
    )

    resume_text = """
    AI/ML Engineer with 1 year of experience.

    Software Engineering Intern.

    Skills:
    Python, C++, PyTorch, TensorFlow, SQL.
    """

    profile = build_candidate_profile(
        resume_text,
        base_profile=base_profile,
    )

    # Resume-derived fields should be populated.
    assert profile.skills
    assert profile.resume_roles
    assert profile.experience_years == 1.0
    assert profile.career_level == "intern"

    # Explicit user preferences MUST remain unchanged.
    assert profile.preferred_roles == [
        "AI Engineer",
        "ML Engineer",
        "Machine Learning Engineer",
        "LLM Engineer",
        "Applied Scientist",
        "Research Engineer",
    ]

    assert profile.preferred_locations == [
        "India",
        "Bengaluru",
        "Hyderabad",
        "Pune",
        "Remote",
    ]


def test_resume_can_build_profile_without_base_profile():
    resume_text = """
    Machine Learning Engineer with 1 year of experience.

    Skills:
    Python, PyTorch, TensorFlow, SQL.
    """

    profile = build_candidate_profile(
        resume_text
    )

    assert isinstance(
        profile,
        CandidateProfile,
    )

    assert profile.skills
    assert profile.resume_roles
    assert profile.experience_years == 1.0
    assert profile.career_level != "unknown"
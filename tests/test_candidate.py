from app.models.candidate import CandidateProfile


def test_candidate_profile():

    candidate = CandidateProfile(
        name="Test User",
        email="test@example.com",
        location="India",
        preferred_roles=["Software Engineer"],
        skills=["Python", "C++"],
    )

    assert candidate.name == "Test User"
    assert "Python" in candidate.skills
    assert "Software Engineer" in candidate.preferred_roles
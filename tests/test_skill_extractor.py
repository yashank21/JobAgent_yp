from app.services.skill_extractor import extract_skills


def test_extract_skills():

    text = """
    We are looking for a Software Engineer
    with experience in Python, C++, SQL,
    and Machine Learning.
    """

    result = extract_skills(text)

    assert "python" in result
    assert "c++" in result
    assert "sql" in result
    assert "machine learning" in result


def test_extract_skills_case_insensitive():

    text = """
    Experience with PYTHON, PyTorch,
    FASTAPI and PostgreSQL.
    """

    result = extract_skills(text)

    assert "python" in result
    assert "pytorch" in result
    assert "fastapi" in result
    assert "postgresql" in result


def test_extract_skills_empty_text():

    assert extract_skills("") == []


def test_extract_skills_no_known_skills():

    text = """
    Excellent communication skills.
    Strong problem-solving ability.
    """

    assert extract_skills(text) == []


def test_custom_skill_vocabulary():

    text = """
    Experience with Rust and Golang.
    """

    result = extract_skills(
        text,
        skills={"rust", "golang"},
    )

    assert result == ["go", "rust"]
    
def test_extract_specialized_technical_skills():

    text = """
    Experience with OpenFOAM, ANSYS Fluent,
    COMSOL Multiphysics, ParaView, Three.js,
    SQLAlchemy and HPC environments.
    """

    result = extract_skills(text)

    assert "openfoam" in result
    assert "ansys fluent" in result
    assert "comsol multiphysics" in result
    assert "paraview" in result
    assert "three.js" in result
    assert "sqlalchemy" in result
    assert "hpc" in result
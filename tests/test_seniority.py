from app.eligibility.seniority import classify_seniority


def test_senior_software_engineer():
    assert (
        classify_seniority("Senior Software Engineer")
        == "senior"
    )


def test_sr_software_engineer():
    assert (
        classify_seniority("Sr. Software Engineer")
        == "senior"
    )


def test_staff_engineer():
    assert (
        classify_seniority("Staff Software Engineer")
        == "senior"
    )


def test_ai_engineer_is_mid():
    assert (
        classify_seniority("AI Engineer")
        == "mid"
    )


def test_machine_learning_engineer_is_mid():
    assert (
        classify_seniority("Machine Learning Engineer")
        == "mid"
    )


def test_new_grad_is_entry():
    assert (
        classify_seniority("New Graduate Software Engineer")
        == "entry"
    )


def test_intern():
    assert (
        classify_seniority("Software Engineering Intern")
        == "intern"
    )


def test_engineering_manager():
    assert (
        classify_seniority("Engineering Manager")
        == "manager"
    )
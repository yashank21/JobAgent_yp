from app.scoring.role_normalizer import (
    RoleFamily,
    classify_role,
    normalize_role_title,
)


def test_normalize_role_title():
    result = normalize_role_title(
        "New Graduate Engineer, Software - '26/'27 (Starlink)"
    )

    assert "software" in result
    assert "26" not in result
    assert "27" not in result


def test_software_engineer():
    assert (
        classify_role("Software Engineer")
        == RoleFamily.SOFTWARE_ENGINEERING
    )


def test_new_grad_software_engineer():
    assert (
        classify_role(
            "New Graduate Engineer, Software - '26/'27"
        )
        == RoleFamily.SOFTWARE_ENGINEERING
    )


def test_software_development_engineer():
    assert (
        classify_role("Software Development Engineer")
        == RoleFamily.SOFTWARE_ENGINEERING
    )


def test_machine_learning_engineer():
    assert (
        classify_role("Machine Learning Engineer")
        == RoleFamily.MACHINE_LEARNING
    )


def test_ml_engineer():
    assert (
        classify_role("ML Engineer")
        == RoleFamily.MACHINE_LEARNING
    )


def test_data_engineer():
    assert (
        classify_role("Data Engineer")
        == RoleFamily.DATA_ENGINEERING
    )


def test_backend_engineer():
    assert (
        classify_role("Backend Engineer")
        == RoleFamily.BACKEND_ENGINEERING
    )


def test_frontend_engineer():
    assert (
        classify_role("Frontend Engineer")
        == RoleFamily.FRONTEND_ENGINEERING
    )


def test_devops_engineer():
    assert (
        classify_role("DevOps Engineer")
        == RoleFamily.DEVOPS
    )


def test_unknown_role():
    assert (
        classify_role("Mechanical Engineer")
        == RoleFamily.UNKNOWN
    )


def test_empty_title():
    assert classify_role("") == RoleFamily.UNKNOWN
    
def test_supplier_development_engineer_is_not_software_engineering():
    assert classify_role(
        "Supplier Development Engineer (Mechanical Engineering)"
    ) == RoleFamily.UNKNOWN


def test_production_control_scheduler_is_unknown():
    assert classify_role(
        "Production Control Scheduler (Falcon)"
    ) == RoleFamily.UNKNOWN


def test_environmental_health_safety_engineer_is_unknown():
    assert classify_role(
        "Environmental Health & Safety Engineer (Satellites)"
    ) == RoleFamily.UNKNOWN


def test_software_engineer_is_software_engineering():
    assert classify_role(
        "Software Engineer"
    ) == RoleFamily.SOFTWARE_ENGINEERING


def test_software_development_engineer_is_software_engineering():
    assert classify_role(
        "Software Development Engineer"
    ) == RoleFamily.SOFTWARE_ENGINEERING


def test_new_grad_software_engineer_is_software_engineering():
    assert classify_role(
        "New Graduate Engineer, Software - '26/'27 (Starlink)"
    ) == RoleFamily.SOFTWARE_ENGINEERING
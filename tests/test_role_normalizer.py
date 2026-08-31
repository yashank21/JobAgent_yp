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
    
def test_ai_engineer():
    assert classify_role(
        "AI Engineer"
    ) == RoleFamily.AI_ENGINEERING


def test_applied_ai_engineer():
    assert classify_role(
        "Applied AI Engineer"
    ) == RoleFamily.AI_ENGINEERING


def test_llm_engineer():
    assert classify_role(
        "LLM Engineer"
    ) == RoleFamily.LLM_GENAI


def test_generative_ai_engineer():
    assert classify_role(
        "Generative AI Engineer"
    ) == RoleFamily.LLM_GENAI


def test_genai_engineer():
    assert classify_role(
        "GenAI Engineer"
    ) == RoleFamily.LLM_GENAI


def test_rag_engineer():
    assert classify_role(
        "RAG Engineer"
    ) == RoleFamily.LLM_GENAI


def test_machine_learning_engineer():
    assert classify_role(
        "Machine Learning Engineer"
    ) == RoleFamily.MACHINE_LEARNING


def test_ai_ml_engineer():
    assert classify_role(
        "AI/ML Engineer"
    ) == RoleFamily.AI_ENGINEERING


def test_forward_deployed_engineer():
    assert classify_role(
        "Forward Deployed Engineer"
    ) == RoleFamily.FORWARD_DEPLOYED


def test_data_scientist():
    assert classify_role(
        "Data Scientist"
    ) == RoleFamily.DATA_SCIENCE


def test_applied_scientist():
    assert classify_role(
        "Applied Scientist"
    ) == RoleFamily.DATA_SCIENCE


def test_data_platform_engineer():
    assert classify_role(
        "Data Platform Engineer"
    ) == RoleFamily.DATA_ENGINEERING


def test_ml_platform_engineer():
    assert classify_role(
        "ML Platform Engineer"
    ) == RoleFamily.DEVOPS_ML_PLATFORM

def test_software_engineer_ai_ml_is_not_generic_software():
    assert classify_role(
        "Software Engineer, AI/ML"
    ) == RoleFamily.AI_ENGINEERING


def test_software_engineer_generative_ai_is_not_generic_software():
    assert classify_role(
        "Software Engineer, Generative AI"
    ) == RoleFamily.LLM_GENAI


def test_backend_software_engineer_is_backend():
    assert classify_role(
        "Backend Software Engineer"
    ) == RoleFamily.BACKEND_ENGINEERING
    
def test_sde():
    assert classify_role(
        "SDE"
    ) == RoleFamily.SOFTWARE_ENGINEERING


def test_software_engineer_with_backend():
    assert classify_role(
        "Software Engineer - Backend"
    ) == RoleFamily.SOFTWARE_ENGINEERING


def test_software_engineer_with_ai():
    assert classify_role(
        "Software Engineer, AI"
    ) == RoleFamily.AI_ENGINEERING


def test_software_engineer_with_ml():
    assert classify_role(
        "Software Engineer, Machine Learning"
    ) == RoleFamily.MACHINE_LEARNING


def test_software_engineer_with_llm():
    assert classify_role(
        "Software Engineer - LLM"
    ) == RoleFamily.LLM_GENAI


def test_applied_machine_learning_engineer():
    assert classify_role(
        "Applied Machine Learning Engineer"
    ) == RoleFamily.MACHINE_LEARNING


def test_deep_learning_engineer():
    assert classify_role(
        "Deep Learning Engineer"
    ) == RoleFamily.MACHINE_LEARNING


def test_mle():
    assert classify_role(
        "MLE"
    ) == RoleFamily.MACHINE_LEARNING


def test_ai_software_engineer():
    assert classify_role(
        "AI Software Engineer"
    ) == RoleFamily.AI_ENGINEERING


def test_machine_learning_scientist():
    assert classify_role(
        "Machine Learning Scientist"
    ) == RoleFamily.DATA_SCIENCE


def test_research_engineer_is_research_engineering():
    assert classify_role(
        "Research Engineer"
    ) == RoleFamily.RESEARCH_ENGINEERING
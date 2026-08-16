"""
Candidate profile configuration.

Represents Yashank's current professional profile
used by the job-matching pipeline.
"""

from app.models.candidate import CandidateProfile


CANDIDATE_PROFILE = CandidateProfile(
    name="Yashank Patidar",
    email="yashankpatidar21@gmail.com",
    location="India",

    preferred_roles=[
        "AI/ML Engineer",
        "Machine Learning Engineer",
        "Software Engineer",
        "Software Engineering",
        "Backend Engineer",
    ],

    preferred_locations=[
        "India",
        "Remote",
    ],

    minimum_salary_lpa=0.0,

    # Juniper Networks:
    # June 2025 -> May 2026 = 11 months
    experience_years=11 / 12,

    skills=[
        # Programming
        "Python",
        "C++",
        "SQL",

        # Generative AI / LLM
        "Large Language Models",
        "Retrieval-Augmented Generation",
        "Prompt Engineering",
        "LangChain",

        # AI / ML
        "PyTorch",
        "TensorFlow",
        "Scikit-learn",
        "GANs",
        "Transformers",
        "DeBERTa",
        "ViT",

        # Computer Vision / NLP
        "Computer Vision",
        "Natural Language Processing",
        "OCR",
        "Named Entity Recognition",

        # Data / Backend
        "Pandas",
        "NumPy",

        # Tools
        "Git",
        "VS Code",
        "Jupyter Notebook",
        "Google Colab",

        # CS fundamentals
        "Data Structures & Algorithms",
        "Object-Oriented Programming",
        "Operating Systems",
        "Computer Networks",
        "DBMS",
    ],

    education=[
        "MTech Information Technology - NIT Karnataka",
        "BTech Computer Science Engineering - Medi-Caps University",
    ],

    projects=[
        "2D Image to 3D Voxel Reconstruction using GANs",
        "Multimodal Meme Classification using Transformers",
        "Retrieval-Augmented Generation chatbot",
    ],

    github_url="https://github.com/yashank21",
)
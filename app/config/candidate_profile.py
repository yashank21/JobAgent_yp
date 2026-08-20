"""
Candidate profile configuration.

Represents Yashank's current professional profile
used by the job-matching pipeline.
"""

from app.models.candidate import CandidateProfile

CANDIDATE_PROFILE = CandidateProfile(
    name="Yashank Patidar",
    email="yashank21@gmail.com",
    location="India",
    
    # -----------------------------------------
    # Experience (11 months at Juniper Networks)
    # -----------------------------------------
    experience_years=11 / 12,  # ~0.917 years (0-1 year entry level)

    # -----------------------------------------
    # Location Preferences
    # -----------------------------------------
    preferred_locations=[
        "India",
        "Bengaluru",
        "Bangalore",
        "Hyderabad",
        "Pune",
        "Noida",
        "Gurugram",
        "Remote - India",
        "Remote",
    ],

    # -----------------------------------------
    # Target Roles
    # -----------------------------------------
    preferred_roles=[
    "AI Engineer",
    "ML Engineer",
    "Machine Learning Engineer",
    "LLM Engineer",
    "Applied Scientist",
    "Research Engineer",
],

    secondary_roles=[
        "Software Engineer",
        "Backend Engineer",
    ],

    # -----------------------------------------
    # Technical Skills
    # Includes exact tokens, canonical short-forms, and expanded forms
    # -----------------------------------------
    skills=[
        # Programming & Core CS
        "Python", "python",
        "C++", "c++",
        "SQL", "sql",
        "Data Structures & Algorithms", "Data Structures", "Algorithms", "DSA", "dsa",
        "Object-Oriented Programming", "OOP",
        "Operating Systems", "OS",
        "Computer Networks", "Networking",
        "DBMS", "Database Management Systems",

        # Generative AI, LLMs & NLP
        "Large Language Models", "Large Language Model", "LLM", "llm",
        "Retrieval-Augmented Generation", "Retrieval Augmented Generation", "RAG", "rag",
        "Prompt Engineering",
        "LangChain", "langchain",
        "Natural Language Processing", "NLP", "nlp",
        "Named Entity Recognition", "NER",
        "Transformers", "transformers",
        "DeBERTa", "deberta",

        # Core AI / ML & Deep Learning
        "Machine Learning", "machine learning", "ML", "ml",
        "Artificial Intelligence", "AI", "ai",
        "Deep Learning", "DL", "dl",
        "PyTorch", "pytorch",
        "TensorFlow", "tensorflow",
        "Scikit-learn", "scikit-learn", "sklearn",
        "GANs", "Generative Adversarial Networks",

        # Computer Vision & Multimodal
        "Computer Vision", "computer vision", "CV", "cv",
        "Vision Transformer", "ViT", "vit",
        "OCR", "Optical Character Recognition",

        # Data, Backend & Tools
        "Pandas", "pandas",
        "NumPy", "numpy",
        "FastAPI", "fastapi",
        "Git", "git",
        "VS Code",
        "Jupyter Notebook",
        "Google Colab",
        "Unit Testing", "Testing",
    ],

    # -----------------------------------------
    # Education
    # -----------------------------------------
    education=[
        "MTech Information Technology - NIT Karnataka",
        "BTech Computer Science Engineering - Medi-Caps University",
    ],

    # -----------------------------------------
    # Key Projects
    # -----------------------------------------
    projects=[
        "2D Image to 3D Voxel Reconstruction using GANs",
        "Multimodal Meme Classification using Transformers",
        "Retrieval-Augmented Generation chatbot",
    ],

    # -----------------------------------------
    # Compensation & Links
    # -----------------------------------------
    minimum_salary_lpa=0.0,
    github_url="https://github.com/yashank21",
)
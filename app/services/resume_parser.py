"""
Resume file parser.

Supports:
- PDF
- DOCX

Responsibility:
    Convert a resume file into plain text.

This module does NOT:
- classify roles
- extract skills
- infer experience
- modify CandidateProfile
"""

from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract plain text from a PDF resume."""

    path = Path(file_path)

    reader = PdfReader(str(path))

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text.strip())

    return "\n\n".join(pages).strip()


def extract_text_from_docx(file_path: str | Path) -> str:
    """Extract plain text from a DOCX resume."""

    path = Path(file_path)

    document = Document(str(path))

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs).strip()


def extract_resume_text(file_path: str | Path) -> str:
    """
    Extract plain text from a supported resume file.

    Raises:
        ValueError: If the file type is unsupported.
        FileNotFoundError: If the file does not exist.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Resume file not found: {path}"
        )

    extension = path.suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(path)

    if extension == ".docx":
        return extract_text_from_docx(path)

    raise ValueError(
        f"Unsupported resume format: {extension}. "
        f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    )
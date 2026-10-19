import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import docx
import fitz  # PyMuPDF

from jobpilot.config import BASE_DIR
from jobpilot.logger import logger
from jobpilot.models.schemas import CandidateProfile
from jobpilot.sources.deduplicator import KNOWN_SKILLS, extract_skills_from_text


class ResumeParser:
    """Extracts text, skills, and projects from uploaded PDF and DOCX files."""

    RESUME_STORAGE_DIR = BASE_DIR / "data" / "resumes"

    def __init__(self):
        self.RESUME_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def extract_text_from_pdf(self, file_path: Path | str) -> str:
        """Extracts plain text from a PDF file using PyMuPDF (fitz)."""
        text_parts = []
        try:
            doc = fitz.open(str(file_path))
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            return "\n".join(text_parts).strip()
        except Exception as e:
            logger.error(f"Failed to read PDF file {file_path}: {e}")
            raise ValueError(f"Unable to parse PDF: {str(e)}")

    def extract_text_from_docx(self, file_path: Path | str) -> str:
        """Extracts plain text from a DOCX file using python-docx."""
        try:
            doc = docx.Document(str(file_path))
            full_text = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(full_text).strip()
        except Exception as e:
            logger.error(f"Failed to read DOCX file {file_path}: {e}")
            raise ValueError(f"Unable to parse DOCX: {str(e)}")

    def parse_file(self, file_path: Path | str) -> Dict[str, Any]:
        """Reads file, extracts text, identified skills, and analyzes content."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".pdf":
            raw_text = self.extract_text_from_pdf(path)
        elif ext in (".docx", ".doc"):
            raw_text = self.extract_text_from_docx(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Only PDF and DOCX are supported.")

        skills = extract_skills_from_text(raw_text)

        # Detect candidate projects mentioned in text
        project_candidates = []
        lines = raw_text.splitlines()
        for i, line in enumerate(lines):
            line_clean = line.strip()
            if any(k in line_clean.lower() for k in ["project", "developed", "built", "implemented", "predictor", "system", "chatbot"]):
                if 5 < len(line_clean) < 100:
                    project_candidates.append(line_clean)

        # Missing information analysis for a fresher AI/ML role
        missing_recommendations = []
        if not any(k in raw_text.lower() for k in ["github.com", "linkedin.com"]):
            missing_recommendations.append("Consider adding your GitHub or LinkedIn profile link.")
        if not any(s in skills for s in ["Git", "Docker", "FastAPI"]):
            missing_recommendations.append("Listing tools like Git, FastAPI, or Docker can enhance AI engineer profile visibility.")

        return {
            "filename": path.name,
            "file_path": str(path),
            "extracted_text": raw_text,
            "parsed_skills": skills,
            "parsed_projects": project_candidates[:8],
            "recommendations": missing_recommendations,
            "char_count": len(raw_text),
        }

    def save_uploaded_file(self, file_bytes: bytes, original_filename: str) -> Path:
        """Saves uploaded resume securely in local private directory."""
        # Sanitize filename
        safe_name = Path(original_filename).name
        target_path = self.RESUME_STORAGE_DIR / safe_name
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        return target_path


resume_parser = ResumeParser()

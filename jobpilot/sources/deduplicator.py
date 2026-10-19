import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse, urlunparse

from jobpilot.models.schemas import Job


# Known tech skills dictionary for regex matching
KNOWN_SKILLS = [
    "Python", "NumPy", "Pandas", "Scikit-learn", "SQL",
    "OpenCV", "MediaPipe", "YOLO", "LangChain", "LangGraph",
    "Hugging Face", "Flask", "FastAPI", "HTML", "CSS", "JavaScript",
    "MySQL", "MongoDB", "TensorFlow", "PyTorch", "Docker", "Kubernetes",
    "AWS", "GCP", "Git", "REST API", "NLP", "Computer Vision",
    "Deep Learning", "Machine Learning", "Data Analysis", "Generative AI",
    "LLM", "C++", "Java", "R", "Tableau", "Power BI"
]


def canonicalize_url(url: str) -> str:
    """Strip tracking query parameters like utm_*, ref, etc. to produce canonical URL."""
    try:
        parsed = urlparse(url.strip())
        # Filter out common analytics parameters
        query_parts = []
        if parsed.query:
            for part in parsed.query.split("&"):
                if part and not any(part.lower().startswith(p) for p in ["utm_", "ref=", "gh_jid=", "source="]):
                    query_parts.append(part)
        clean_query = "&".join(query_parts)
        # Drop trailing slash from path
        clean_path = parsed.path.rstrip("/")
        return urlunparse((parsed.scheme, parsed.netloc.lower(), clean_path, parsed.params, clean_query, ""))
    except Exception:
        return url.strip().lower()


def generate_job_id(source_name: str, source_id: Optional[str], url: str, title: str, company: str) -> str:
    """Generate a deterministic SHA256 hex string identifying the job."""
    canon_url = canonicalize_url(url) if url else ""
    if source_id and source_name:
        key = f"{source_name.lower()}::{source_id}::{company.lower()}"
    elif canon_url:
        key = f"{canon_url}"
    else:
        key = f"{company.lower()}::{title.lower()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def clean_html_text(html_content: str) -> str:
    """Clean HTML tags and decode entities into readable plain text."""
    if not html_content:
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", html_content)
    # Normalize whitespaces
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def extract_skills_from_text(text: str) -> List[str]:
    """Extract recognized skills present in the text."""
    if not text:
        return []
    found_skills = []
    text_lower = f" {text.lower()} "
    for skill in KNOWN_SKILLS:
        # Use word boundaries for matching skills
        pattern = r"(?i)\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.append(skill)
    return sorted(list(set(found_skills)))


def extract_experience_requirements(text: str) -> Tuple[float, Optional[float]]:
    """
    Extract min and max experience years from job text.
    Returns (min_years, max_years).
    """
    if not text:
        return 0.0, 1.0

    lower = text.lower()

    # Look for fresher / internship / 2027 graduate keywords
    if any(k in lower for k in ["fresher", "entry level", "entry-level", "intern", "internship", "college graduate", "0-1 year", "0 to 1 year", "graduating in 2027", "no experience required"]):
        return 0.0, 1.0

    # Pattern: X to Y years / X-Y years
    range_match = re.search(r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)", lower)
    if range_match:
        min_y = float(range_match.group(1))
        max_y = float(range_match.group(2))
        return min_y, max_y

    # Pattern: X+ years / X years of experience
    min_match = re.search(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience", lower)
    if min_match:
        min_y = float(min_match.group(1))
        return min_y, min_y + 2.0

    # Default to 0.0, 1.0 if unspecified
    return 0.0, 1.0


class JobDeduplicator:
    """Deduplicates job postings based on canonical IDs, canonical URLs, and content similarity."""

    @staticmethod
    def deduplicate(jobs: List[Job]) -> Tuple[List[Job], int]:
        """
        Deduplicates a list of Job objects across multi-platform sources.
        Preserves all source application links on the surviving Job record.
        Returns (unique_jobs, duplicate_count).
        """
        id_to_job: Dict[str, Job] = {}
        title_company_loc_to_job: Dict[Tuple[str, str, str], Job] = {}
        canon_url_to_job: Dict[str, Job] = {}
        duplicate_count = 0

        for job in jobs:
            # Ensure the job's own source URL is in alternate_source_urls
            if job.url and job.source_name:
                job.alternate_source_urls.setdefault(job.source_name, job.url)

            canon_url = canonicalize_url(job.url) if job.url else ""

            # Check 1: By deterministic ID
            existing = id_to_job.get(job.id)

            # Check 2: By Canonical URL
            if not existing and canon_url and canon_url in canon_url_to_job:
                existing = canon_url_to_job[canon_url]

            # Check 3: By normalized (company, title, location/workplace)
            norm_comp = re.sub(r"[^a-z0-9]", "", job.company.lower())
            norm_title = re.sub(r"[^a-z0-9]", "", job.title.lower())
            # Normalize location (treat remote identically)
            norm_loc = "remote" if job.is_remote else re.sub(r"[^a-z0-9]", "", job.location.lower())
            key = (norm_comp, norm_title, norm_loc)

            if not existing and key in title_company_loc_to_job:
                existing = title_company_loc_to_job[key]

            if existing:
                # Duplicate found! Preserve source links from the duplicate onto the existing job
                duplicate_count += 1
                if job.url:
                    existing.alternate_source_urls[job.source_name] = job.url
                for src_name, src_url in job.alternate_source_urls.items():
                    existing.alternate_source_urls[src_name] = src_url
                # Merge any missing skills
                for sk in job.required_skills:
                    if sk not in existing.required_skills:
                        existing.required_skills.append(sk)
            else:
                id_to_job[job.id] = job
                if canon_url:
                    canon_url_to_job[canon_url] = job
                title_company_loc_to_job[key] = job

        unique = list(id_to_job.values())
        return unique, duplicate_count

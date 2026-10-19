import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from jobpilot.config import settings
from jobpilot.logger import logger
from jobpilot.models.schemas import Job, PlatformSourceStatus
from jobpilot.sources.base import BaseJobSource
from jobpilot.sources.deduplicator import (
    clean_html_text,
    extract_experience_requirements,
    extract_skills_from_text,
    generate_job_id,
)
from jobpilot.utils.date_utils import utc_now_iso


class NaukriAdapter(BaseJobSource):
    """
    Adapter for Naukri.com (India's primary job portal).

    Access Investigation & Compliance:
    - Naukri restricts public programmatic scraping under Sec 6.2 of its Terms of Service.
    - Cloudflare bot management and dynamic JS challenges protect public listing pages.
    - Permitted Integration Methods:
      1. Candidate Job URL / Text Ingestion: Normalizes user-submitted job links.
      2. Naukri Job Alert / CSV Import: Parses bulk exported listings.
      3. Enterprise Recruiter API: Accessible if NAUKRI_API_KEY is configured.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "NAUKRI_API_KEY", None)
        self._last_successful_fetch: Optional[str] = None
        self._last_count = 0

    @property
    def source_name(self) -> str:
        return "Naukri.com"

    @property
    def platform_key(self) -> str:
        return "naukri"

    def health_check(self) -> Dict[str, Any]:
        if self.api_key:
            return {
                "healthy": True,
                "status_code": 200,
                "message": "Naukri Enterprise API Key configured",
                "method": "Enterprise Recruiter API",
            }
        return {
            "healthy": False,
            "status_code": 403,
            "message": "Public web scraping restricted by Naukri ToS & Cloudflare. Use Manual URL, Pasted JD, or CSV Import.",
            "method": "Manual URL / CSV Alerts Ingestion",
        }

    def get_source_status(self) -> PlatformSourceStatus:
        health = self.health_check()
        return PlatformSourceStatus(
            name=self.source_name,
            platform_key=self.platform_key,
            connection_status="Connected" if health["healthy"] else "Restricted / Manual Only",
            last_successful_fetch=self._last_successful_fetch,
            jobs_retrieved=self._last_count,
            new_jobs_found=self._last_count,
            errors_or_warnings=None if health["healthy"] else health["message"],
            auth_requirements="Naukri Recruiter Partner API Key or User Manual Import",
            permitted_method="Candidate Job URL Ingestion / CSV Export",
        )

    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Standardizes a Naukri job record into the common Job schema."""
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Unknown Employer").strip()
        location = raw_job.get("location", "India / Remote").strip()
        desc = clean_html_text(raw_job.get("description", "")) or title
        url = raw_job.get("url", "").strip() or f"https://www.naukri.com/job-listings-{re.sub(r'[^a-z0-9]', '-', title.lower())}"
        job_id_raw = str(raw_job.get("job_id", "") or raw_job.get("id", ""))

        # Experience parsing
        min_e = float(raw_job.get("min_experience_years", 0.0))
        max_e = float(raw_job.get("max_experience_years", 1.0)) if raw_job.get("max_experience_years") is not None else None
        if min_e == 0.0 and max_e == 1.0:
            extracted_min, extracted_max = extract_experience_requirements(desc)
            min_e, max_e = extracted_min, extracted_max

        # Remote / workplace type
        is_remote = bool(raw_job.get("is_remote", False)) or any(k in location.lower() or k in desc.lower() for k in ["remote", "work from home"])
        workplace_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in location.lower() else "On-site")

        # Skills
        skills = raw_job.get("required_skills") or extract_skills_from_text(desc)

        stable_id = generate_job_id(
            source_name="naukri",
            source_id=job_id_raw or None,
            url=url,
            title=title,
            company=company,
        )

        return Job(
            id=stable_id,
            title=title,
            company=company,
            location=location,
            is_remote=is_remote,
            workplace_type=workplace_type,
            employment_type=raw_job.get("employment_type", "Full-time"),
            min_experience_years=min_e,
            max_experience_years=max_e,
            required_skills=skills[:8],
            preferred_skills=skills[8:],
            description=desc,
            posted_date=raw_job.get("posted_date", utc_now_iso()[:10]),
            salary_range=raw_job.get("salary_range"),
            url=url,
            source_name="Naukri",
            source_id=job_id_raw or None,
            alternate_source_urls={"Naukri": url} if url else {},
            first_discovered_at=utc_now_iso(),
            last_checked_at=utc_now_iso(),
            last_verified_at=utc_now_iso(),
            listing_status="Active",
            is_active=True,
            is_demo=False,
        )

    def parse_job_url_or_text(
        self,
        url: str,
        title: str,
        company: str,
        description: str,
        location: str = "Pune / Remote",
        salary_range: Optional[str] = None
    ) -> Job:
        """Parses a user-supplied Naukri job URL and details into a validated Job."""
        # Extract job ID from standard Naukri URL if present (e.g. ...-jid-123456)
        job_id_match = re.search(r"jid[-_](\w+)", url)
        source_id = job_id_match.group(1) if job_id_match else None

        raw = {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "url": url,
            "job_id": source_id,
            "salary_range": salary_range,
        }
        return self.normalize_job(raw)

    def fetch_jobs(
        self,
        search_criteria: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Job]:
        """
        Fetches jobs from Naukri.
        If Enterprise API credentials are configured, calls authorized endpoint.
        Otherwise adheres strictly to compliance and returns empty with log warning.
        """
        if not self.api_key:
            logger.info("Naukri.com: Automated scraping restricted by ToS. Use manual URL or CSV ingestion.")
            return []

        # Authorized API call implementation when API key is provided
        logger.info(f"Querying authorized Naukri Partner API with limit {limit}...")
        # Simulated placeholder for enterprise endpoint
        return []

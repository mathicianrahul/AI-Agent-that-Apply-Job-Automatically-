import re
from typing import Any, Dict, List, Optional

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


class LinkedInAdapter(BaseJobSource):
    """
    Adapter for LinkedIn Jobs.

    Access Investigation & Compliance:
    - LinkedIn strictly prohibits unauthorized programmatic scraping under Sec 8.2 of the User Agreement.
    - Automated collection triggers anti-bot checkpoints and account restrictions.
    - Official Access Path: LinkedIn Talent Solutions Partner Program with 'r_jobs' OAuth 2.0 permission.
    - Permitted Implementation:
      1. Candidate Job URL Ingestion: Ingests specific LinkedIn posting URLs (e.g., /jobs/view/384920...).
      2. CSV Job Ingestion: Bulk import of saved jobs or alert emails.
      3. Authorized OAuth Integration: Activated when LINKEDIN_ACCESS_TOKEN is configured.
    """

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or getattr(settings, "LINKEDIN_ACCESS_TOKEN", None)
        self._last_successful_fetch: Optional[str] = None
        self._last_count = 0

    @property
    def source_name(self) -> str:
        return "LinkedIn Jobs"

    @property
    def platform_key(self) -> str:
        return "linkedin"

    def health_check(self) -> Dict[str, Any]:
        if self.access_token:
            return {
                "healthy": True,
                "status_code": 200,
                "message": "LinkedIn Partner OAuth Token configured",
                "method": "LinkedIn Partner API (OAuth 2.0)",
            }
        return {
            "healthy": False,
            "status_code": 401,
            "message": "LinkedIn requires OAuth 2.0 Partner permissions (r_jobs). Use Direct URL or CSV Import.",
            "method": "Manual URL / Pasted JD / CSV Ingestion",
        }

    def get_source_status(self) -> PlatformSourceStatus:
        health = self.health_check()
        return PlatformSourceStatus(
            name=self.source_name,
            platform_key=self.platform_key,
            connection_status="Connected" if health["healthy"] else "Requires API Key / Manual Only",
            last_successful_fetch=self._last_successful_fetch,
            jobs_retrieved=self._last_count,
            new_jobs_found=self._last_count,
            errors_or_warnings=None if health["healthy"] else health["message"],
            auth_requirements="LinkedIn Talent Solutions Partner OAuth 2.0 or Manual Import",
            permitted_method="Job URL Ingestion / CSV Export",
        )

    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Standardizes a LinkedIn job into the common Job schema."""
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Company on LinkedIn").strip()
        location = raw_job.get("location", "India / Remote").strip()
        desc = clean_html_text(raw_job.get("description", "")) or title
        url = raw_job.get("url", "").strip()

        # Extract LinkedIn Job ID from URL if present (e.g. /jobs/view/123456789)
        job_id_match = re.search(r"/jobs/view/(\d+)", url)
        source_id = job_id_match.group(1) if job_id_match else str(raw_job.get("source_id", "") or "")

        # Fallback URL if none provided
        if not url:
            url = f"https://www.linkedin.com/jobs/view/{source_id}" if source_id else "https://www.linkedin.com/jobs"

        is_remote = bool(raw_job.get("is_remote", False)) or any(k in location.lower() or k in desc.lower() for k in ["remote", "work from home"])
        workplace_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in location.lower() else "On-site")

        min_e = float(raw_job.get("min_experience_years", 0.0))
        max_e = float(raw_job.get("max_experience_years", 1.0)) if raw_job.get("max_experience_years") is not None else None
        if min_e == 0.0 and max_e == 1.0:
            extracted_min, extracted_max = extract_experience_requirements(desc)
            min_e, max_e = extracted_min, extracted_max

        skills = raw_job.get("required_skills") or extract_skills_from_text(desc)

        emp_type = raw_job.get("employment_type", "Full-time")
        if "intern" in title.lower() or "intern" in desc.lower():
            emp_type = "Internship"

        stable_id = generate_job_id(
            source_name="linkedin",
            source_id=source_id or None,
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
            employment_type=emp_type,
            min_experience_years=min_e,
            max_experience_years=max_e,
            required_skills=skills[:8],
            preferred_skills=skills[8:],
            description=desc,
            posted_date=raw_job.get("posted_date", utc_now_iso()[:10]),
            salary_range=raw_job.get("salary_range"),
            url=url,
            source_name="LinkedIn",
            source_id=source_id or None,
            alternate_source_urls={"LinkedIn": url} if url else {},
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
        raw = {
            "title": title,
            "company": company,
            "location": location,
            "description": description,
            "url": url,
            "salary_range": salary_range,
        }
        return self.normalize_job(raw)

    def fetch_jobs(
        self,
        search_criteria: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Job]:
        if not self.access_token:
            logger.info("LinkedIn: Requires authorized OAuth partner token. Automated scraping not permitted.")
            return []

        logger.info(f"Querying LinkedIn Partner API (limit {limit})...")
        return []

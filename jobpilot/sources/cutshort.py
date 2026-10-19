import re
from typing import Any, Dict, List, Optional

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


class CutshortAdapter(BaseJobSource):
    """
    Adapter for Cutshort (India tech & AI talent matchmaking platform).

    Access Investigation & Compliance:
    - Cutshort is a proprietary recruiter matchmaking system without a public candidate search API.
    - Anti-bot and authentication guard the candidate app.
    - Permitted Methods:
      1. Candidate Job URL Ingestion: Ingests cutshort.io/job/... links.
      2. CSV / Spreadsheet Ingestion.
    """

    def __init__(self):
        self._last_successful_fetch: Optional[str] = None
        self._last_count = 0

    @property
    def source_name(self) -> str:
        return "Cutshort"

    @property
    def platform_key(self) -> str:
        return "cutshort"

    def health_check(self) -> Dict[str, Any]:
        return {
            "healthy": False,
            "status_code": 403,
            "message": "Cutshort has no public search API. Use Candidate URL or CSV Import.",
            "method": "Manual URL / Match Ingestion",
        }

    def get_source_status(self) -> PlatformSourceStatus:
        health = self.health_check()
        return PlatformSourceStatus(
            name=self.source_name,
            platform_key=self.platform_key,
            connection_status="Restricted / Manual Only",
            last_successful_fetch=self._last_successful_fetch,
            jobs_retrieved=self._last_count,
            new_jobs_found=self._last_count,
            errors_or_warnings=health["message"],
            auth_requirements="Matchmaking Portal Account",
            permitted_method="Job URL Ingestion / CSV Export",
        )

    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Employer on Cutshort").strip()
        location = raw_job.get("location", "Pune / Bangalore / Remote").strip()
        desc = clean_html_text(raw_job.get("description", "")) or title
        url = raw_job.get("url", "").strip() or "https://cutshort.io"

        is_remote = bool(raw_job.get("is_remote", False)) or any(k in location.lower() or k in desc.lower() for k in ["remote", "work from home"])
        workplace_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in location.lower() else "On-site")

        id_match = re.search(r"job/([a-zA-Z0-9_-]+)", url)
        source_id = id_match.group(1) if id_match else str(raw_job.get("source_id", "") or "")

        min_e, max_e = extract_experience_requirements(desc)
        skills = raw_job.get("required_skills") or extract_skills_from_text(desc)

        stable_id = generate_job_id(
            source_name="cutshort",
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
            employment_type=raw_job.get("employment_type", "Full-time"),
            min_experience_years=min_e,
            max_experience_years=max_e,
            required_skills=skills[:8],
            preferred_skills=skills[8:],
            description=desc,
            posted_date=raw_job.get("posted_date", utc_now_iso()[:10]),
            salary_range=raw_job.get("salary_range"),
            url=url,
            source_name="Cutshort",
            source_id=source_id or None,
            alternate_source_urls={"Cutshort": url} if url else {},
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
        logger.info("Cutshort: Automated scraping restricted. Ingest via manual URL or CSV.")
        return []

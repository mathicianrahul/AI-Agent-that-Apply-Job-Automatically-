from typing import Any, Dict, List, Optional
import requests

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


class ArbeitnowSource(BaseJobSource):
    """
    Fetches real live job postings from Arbeitnow public job board API.
    URL: https://www.arbeitnow.com/api/job-board-api
    """

    API_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self):
        self._last_successful_fetch: Optional[str] = None
        self._last_count = 0

    @property
    def source_name(self) -> str:
        return "Arbeitnow Public API"

    @property
    def platform_key(self) -> str:
        return "arbeitnow"

    def health_check(self) -> Dict[str, Any]:
        try:
            resp = requests.head(self.API_URL, timeout=8)
            return {
                "healthy": resp.status_code in [200, 301, 302],
                "status_code": resp.status_code,
                "message": "Arbeitnow API reachable" if resp.status_code in [200, 301, 302] else f"HTTP {resp.status_code}",
                "method": "Public REST API (Permitted)",
            }
        except Exception as e:
            return {
                "healthy": False,
                "status_code": None,
                "message": f"Connection error: {str(e)}",
                "method": "Public REST API (Permitted)",
            }

    def normalize_job(self, item: Dict[str, Any]) -> Job:
        slug = str(item.get("slug", ""))
        title = item.get("title", "").strip()
        company = item.get("company_name", "Tech Co").strip()
        location = item.get("location", "Remote")
        is_remote = bool(item.get("remote", False))
        content_html = item.get("description", "")
        description = clean_html_text(content_html) or title
        app_url = item.get("url", "")
        posted_raw = item.get("created_at")
        posted_at = str(posted_raw) if posted_raw is not None else None

        skills = extract_skills_from_text(description)
        for tag in item.get("tags", []):
            if tag not in skills and len(tag) > 1:
                skills.append(tag)

        min_exp, max_exp = extract_experience_requirements(description)

        emp_type = "Full-time"
        job_types = item.get("job_types", [])
        if any("intern" in str(t).lower() for t in job_types):
            emp_type = "Internship"

        stable_id = generate_job_id(
            source_name="arbeitnow",
            source_id=slug,
            url=app_url,
            title=title,
            company=company,
        )

        return Job(
            id=stable_id,
            title=title,
            company=company,
            location=location,
            is_remote=is_remote,
            workplace_type="Remote" if is_remote else "On-site",
            employment_type=emp_type,
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            required_skills=skills[:8],
            preferred_skills=skills[8:],
            description=description,
            posted_date=posted_at,
            salary_range=None,
            url=app_url,
            source_name="Arbeitnow",
            source_id=slug,
            alternate_source_urls={"Arbeitnow": app_url} if app_url else {},
            first_discovered_at=utc_now_iso(),
            last_checked_at=utc_now_iso(),
            last_verified_at=utc_now_iso(),
            listing_status="Active",
            is_active=True,
            is_demo=False,
        )

    def fetch_jobs(
        self,
        search_criteria: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Job]:
        jobs: List[Job] = []
        try:
            logger.info("Fetching live jobs from Arbeitnow public API...")
            resp = requests.get(self.API_URL, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"Arbeitnow returned status {resp.status_code}")
                return jobs

            data = resp.json()
            raw_jobs = data.get("data", [])

            for item in raw_jobs:
                if len(jobs) >= limit:
                    break
                try:
                    job = self.normalize_job(item)
                    if self.validate_job(job):
                        jobs.append(job)
                except Exception as norm_err:
                    logger.debug(f"Error normalizing Arbeitnow job: {norm_err}")

            self._last_successful_fetch = utc_now_iso()
            self._last_count = len(jobs)

        except Exception as e:
            logger.error(f"Failed to fetch Arbeitnow jobs: {e}")

        logger.info(f"Arbeitnow source fetched {len(jobs)} live jobs.")
        return jobs

    def get_source_status(self) -> PlatformSourceStatus:
        health = self.health_check()
        return PlatformSourceStatus(
            name=self.source_name,
            platform_key=self.platform_key,
            connection_status="Connected" if health.get("healthy") else "Error",
            last_successful_fetch=self._last_successful_fetch,
            jobs_retrieved=self._last_count,
            new_jobs_found=self._last_count,
            errors_or_warnings=None if health.get("healthy") else health.get("message"),
            auth_requirements="None (Public API)",
            permitted_method="Public REST API / Open Feeds",
        )

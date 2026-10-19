from typing import Any, Dict, List, Optional
import requests

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


class LeverSource(BaseJobSource):
    """
    Fetches real live job postings from authorized company career websites hosted on Lever ATS.
    Uses official Lever Public Postings API: https://api.lever.co/v0/postings/{company}?mode=json
    """

    DEFAULT_COMPANIES = ["figma", "postman"]

    def __init__(self, companies: Optional[List[str]] = None):
        cfg_companies = [c.strip() for c in getattr(settings, "LEVER_COMPANIES", "figma,postman").split(",") if c.strip()]
        self.companies = companies or cfg_companies or self.DEFAULT_COMPANIES
        self._last_successful_fetch: Optional[str] = None
        self._last_count = 0

    @property
    def source_name(self) -> str:
        return "Company Careers (Lever API)"

    @property
    def platform_key(self) -> str:
        return "lever"

    def health_check(self) -> Dict[str, Any]:
        company = self.companies[0] if self.companies else "postman"
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        try:
            resp = requests.head(url, timeout=8)
            return {
                "healthy": resp.status_code in [200, 301, 302],
                "status_code": resp.status_code,
                "message": "Lever company postings API accessible" if resp.status_code in [200, 301, 302] else f"HTTP {resp.status_code}",
                "method": "Public ATS Postings API",
            }
        except Exception as e:
            return {
                "healthy": False,
                "status_code": None,
                "message": f"Connection error: {str(e)}",
                "method": "Public ATS Postings API",
            }

    def normalize_job(self, item: Dict[str, Any], company_slug: str = "Company") -> Job:
        job_id_num = str(item.get("id", ""))
        title = item.get("text", "").strip()
        categories = item.get("categories", {})
        location_name = categories.get("location", "Remote") or "Remote"
        commitment = categories.get("commitment", "Full-time") or "Full-time"
        workplace_type_raw = str(item.get("workplaceType", "unspecified")).lower()

        description_plain = clean_html_text(item.get("descriptionPlain", "")) or title
        app_url = item.get("hostedUrl", "") or item.get("applyUrl", "")
        created_at_ts = item.get("createdAt")
        posted_at = str(created_at_ts)[:10] if created_at_ts else utc_now_iso()[:10]

        is_remote = workplace_type_raw == "remote" or any(k in location_name.lower() or k in title.lower() for k in ["remote", "home", "anywhere"])
        workplace_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in workplace_type_raw else "On-site")

        skills = extract_skills_from_text(description_plain)
        min_exp, max_exp = extract_experience_requirements(description_plain)

        emp_type = "Full-time"
        if "intern" in commitment.lower() or "intern" in title.lower():
            emp_type = "Internship"

        stable_id = generate_job_id(
            source_name="lever",
            source_id=job_id_num,
            url=app_url,
            title=title,
            company=company_slug.capitalize(),
        )

        return Job(
            id=stable_id,
            title=title,
            company=company_slug.capitalize(),
            location=location_name,
            is_remote=is_remote,
            workplace_type=workplace_type,
            employment_type=emp_type,
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            required_skills=skills[:8],
            preferred_skills=skills[8:],
            description=description_plain,
            posted_date=posted_at,
            salary_range=None,
            url=app_url,
            source_name="Company Careers (Lever)",
            source_id=job_id_num,
            alternate_source_urls={"Lever": app_url} if app_url else {},
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

        for company in self.companies:
            if len(jobs) >= limit:
                break
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            try:
                logger.info(f"Fetching live jobs from Lever company careers: {company}")
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Lever company {company} returned status {resp.status_code}")
                    continue

                raw_jobs = resp.json()
                for item in raw_jobs:
                    if len(jobs) >= limit:
                        break
                    try:
                        job = self.normalize_job(item, company_slug=company)
                        if self.validate_job(job):
                            jobs.append(job)
                    except Exception as norm_err:
                        logger.debug(f"Normalization error on Lever job: {norm_err}")

            except Exception as e:
                logger.error(f"Failed to fetch Lever company {company}: {e}")

        if jobs:
            self._last_successful_fetch = utc_now_iso()
            self._last_count = len(jobs)

        logger.info(f"Lever company source fetched {len(jobs)} live jobs.")
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
            permitted_method="Public ATS REST Postings API",
        )

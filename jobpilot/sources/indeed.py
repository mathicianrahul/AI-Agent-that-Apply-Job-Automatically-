import re
import xml.etree.ElementTree as ET
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


class IndeedAdapter(BaseJobSource):
    """
    Adapter for Indeed India.

    Access Investigation & Compliance:
    - Indeed deprecated its public Publisher search API.
    - Automated web scraping triggers Cloudflare / Datadome anti-bot challenges and violates Terms of Service.
    - Supported Integration Paths:
      1. Employer / Partner XML/RSS Feed: Parses authorized XML job feeds (INDEED_FEED_URL).
      2. Candidate Job URL Ingestion: Ingests specific Indeed viewjob links (jk parameter).
      3. CSV Ingestion: Bulk parsing of candidate exported listings.
    """

    def __init__(self, feed_url: Optional[str] = None):
        self.feed_url = feed_url or getattr(settings, "INDEED_FEED_URL", None)
        self._last_successful_fetch: Optional[str] = None
        self._last_count = 0

    @property
    def source_name(self) -> str:
        return "Indeed India"

    @property
    def platform_key(self) -> str:
        return "indeed"

    def health_check(self) -> Dict[str, Any]:
        if self.feed_url:
            try:
                resp = requests.head(self.feed_url, timeout=8)
                return {
                    "healthy": resp.status_code in [200, 301, 302],
                    "status_code": resp.status_code,
                    "message": "Indeed XML Feed reachable" if resp.status_code in [200, 301, 302] else f"HTTP {resp.status_code}",
                    "method": "Authorized Employer XML Feed",
                }
            except Exception as e:
                return {
                    "healthy": False,
                    "status_code": None,
                    "message": f"Feed error: {str(e)}",
                    "method": "Authorized Employer XML Feed",
                }
        return {
            "healthy": False,
            "status_code": 403,
            "message": "Indeed requires authorized XML Feed or Developer Partner OAuth. Use Manual URL or CSV Import.",
            "method": "Manual URL / XML Feed / CSV Import",
        }

    def get_source_status(self) -> PlatformSourceStatus:
        health = self.health_check()
        return PlatformSourceStatus(
            name=self.source_name,
            platform_key=self.platform_key,
            connection_status="Connected" if health["healthy"] else "Requires Partner Auth / Feed / Manual Only",
            last_successful_fetch=self._last_successful_fetch,
            jobs_retrieved=self._last_count,
            new_jobs_found=self._last_count,
            errors_or_warnings=None if health["healthy"] else health["message"],
            auth_requirements="Indeed Authorized XML Feed or Developer OAuth",
            permitted_method="Employer XML Feed / Candidate Job URL",
        )

    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """Standardizes an Indeed job into the common Job schema."""
        title = raw_job.get("title", "").strip()
        company = raw_job.get("company", "Employer on Indeed").strip()
        location = raw_job.get("location", "India / Remote").strip()
        desc = clean_html_text(raw_job.get("description", "")) or title
        url = raw_job.get("url", "").strip()

        # Extract jk parameter from url if present
        jk_match = re.search(r"jk=([a-zA-Z0-9]+)", url)
        source_id = jk_match.group(1) if jk_match else str(raw_job.get("source_id", "") or "")

        if not url:
            url = f"https://in.indeed.com/viewjob?jk={source_id}" if source_id else "https://in.indeed.com"

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
            source_name="indeed",
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
            source_name="Indeed",
            source_id=source_id or None,
            alternate_source_urls={"Indeed": url} if url else {},
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
        if not self.feed_url:
            logger.info("Indeed: No authorized XML feed configured. Automated scraping not permitted.")
            return []

        jobs: List[Job] = []
        try:
            logger.info(f"Fetching authorized Indeed XML feed from {self.feed_url}...")
            resp = requests.get(self.feed_url, timeout=15)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//job"):
                    if len(jobs) >= limit:
                        break
                    raw = {
                        "title": item.findtext("title", ""),
                        "company": item.findtext("company", ""),
                        "location": item.findtext("city", "") or item.findtext("location", "India"),
                        "description": item.findtext("description", ""),
                        "url": item.findtext("url", ""),
                        "source_id": item.findtext("referencenumber", ""),
                        "posted_date": item.findtext("date", utc_now_iso()[:10]),
                    }
                    job = self.normalize_job(raw)
                    if self.validate_job(job):
                        jobs.append(job)

                self._last_successful_fetch = utc_now_iso()
                self._last_count = len(jobs)
        except Exception as e:
            logger.error(f"Error fetching Indeed XML feed: {e}")

        return jobs

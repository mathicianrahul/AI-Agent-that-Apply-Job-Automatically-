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


class GreenhouseSource(BaseJobSource):
    """
    Fetches real live job postings from public Greenhouse job boards.
    Uses official public Greenhouse API: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """

    DEFAULT_BOARDS = ["canonical", "cloudflare", "gitlab"]

    def __init__(self, board_tokens: Optional[List[str]] = None):
        cfg_boards = [b.strip() for b in getattr(settings, "GREENHOUSE_BOARDS", "canonical,cloudflare,gitlab").split(",") if b.strip()]
        self.board_tokens = board_tokens or cfg_boards or self.DEFAULT_BOARDS
        self._last_successful_fetch: Optional[str] = None
        self._last_count = 0

    @property
    def source_name(self) -> str:
        return "Greenhouse Public API"

    @property
    def platform_key(self) -> str:
        return "greenhouse"

    def health_check(self) -> Dict[str, Any]:
        board = self.board_tokens[0] if self.board_tokens else "canonical"
        url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
        try:
            resp = requests.head(url, timeout=8)
            return {
                "healthy": resp.status_code in [200, 301, 302],
                "status_code": resp.status_code,
                "message": "Greenhouse boards API accessible" if resp.status_code in [200, 301, 302] else f"HTTP {resp.status_code}",
                "method": "Public REST API (Permitted)",
            }
        except Exception as e:
            return {
                "healthy": False,
                "status_code": None,
                "message": f"Connection error: {str(e)}",
                "method": "Public REST API (Permitted)",
            }

    def normalize_job(self, item: Dict[str, Any], board: str = "Company") -> Job:
        job_id_num = str(item.get("id", ""))
        title = item.get("title", "").strip()
        location_name = item.get("location", {}).get("name", "Remote")
        content_html = item.get("content", "")
        description = clean_html_text(content_html) or title
        app_url = item.get("absolute_url", "")
        posted_at = item.get("updated_at")

        is_remote = any(k in location_name.lower() or k in title.lower() for k in ["remote", "home", "anywhere"])
        workplace_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in location_name.lower() else "On-site")

        skills = extract_skills_from_text(description)
        min_exp, max_exp = extract_experience_requirements(description)

        emp_type = "Full-time"
        if "intern" in title.lower() or "intern" in description.lower():
            emp_type = "Internship"

        stable_id = generate_job_id(
            source_name="greenhouse",
            source_id=job_id_num,
            url=app_url,
            title=title,
            company=board.capitalize(),
        )

        return Job(
            id=stable_id,
            title=title,
            company=board.capitalize(),
            location=location_name,
            is_remote=is_remote,
            workplace_type=workplace_type,
            employment_type=emp_type,
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            required_skills=skills[:8],
            preferred_skills=skills[8:],
            description=description,
            posted_date=posted_at,
            salary_range=None,
            url=app_url,
            source_name="Greenhouse",
            source_id=job_id_num,
            alternate_source_urls={"Greenhouse": app_url} if app_url else {},
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

        for board in self.board_tokens:
            if len(jobs) >= limit:
                break
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
            try:
                logger.info(f"Fetching live jobs from Greenhouse board: {board}")
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"Greenhouse board {board} returned status {resp.status_code}")
                    continue

                data = resp.json()
                raw_jobs = data.get("jobs", [])
                for item in raw_jobs:
                    if len(jobs) >= limit:
                        break
                    try:
                        job = self.normalize_job(item, board=board)
                        if self.validate_job(job):
                            jobs.append(job)
                    except Exception as norm_err:
                        logger.debug(f"Normalization error on Greenhouse job: {norm_err}")

            except Exception as e:
                logger.error(f"Failed to fetch Greenhouse board {board}: {e}")

        if jobs:
            self._last_successful_fetch = utc_now_iso()
            self._last_count = len(jobs)

        logger.info(f"Greenhouse source fetched {len(jobs)} live jobs.")
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
            permitted_method="Public REST API / Boards Feed",
        )

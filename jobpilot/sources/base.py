from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from jobpilot.logger import logger
from jobpilot.models.schemas import Job, PlatformSourceStatus
from jobpilot.utils.date_utils import utc_now_iso


class BaseJobSource(ABC):
    """
    Abstract base class establishing the common JobSource interface for all
    multi-platform job aggregators and adapters.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable display name of the job source."""
        pass

    @property
    @abstractmethod
    def platform_key(self) -> str:
        """Unique machine identifier (e.g. 'naukri', 'linkedin', 'greenhouse', 'indeed')."""
        pass

    @abstractmethod
    def fetch_jobs(
        self,
        search_criteria: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[Job]:
        """
        Fetch jobs from the provider and return normalized Job objects.
        Accepts optional search_criteria (e.g. roles, location, remote preference).
        """
        pass

    def normalize_job(self, raw_job: Dict[str, Any]) -> Job:
        """
        Standardizes raw platform data into the unified Job schema.
        Override in subclasses to parse platform-specific JSON/payloads.
        """
        raise NotImplementedError("normalize_job must be implemented by subclass adapter.")

    def validate_job(self, job: Job) -> bool:
        """
        Validates that a Job object meets minimum schema integrity constraints.
        Returns True if valid, False otherwise.
        """
        if not job.title or not job.title.strip():
            logger.warning(f"[{self.source_name}] Validation failed: Empty job title.")
            return False
        if not job.company or not job.company.strip():
            logger.warning(f"[{self.source_name}] Validation failed: Empty company name for '{job.title}'.")
            return False
        if not job.id or not job.id.strip():
            logger.warning(f"[{self.source_name}] Validation failed: Missing deterministic job ID.")
            return False
        if not job.url or not job.url.strip():
            logger.warning(f"[{self.source_name}] Validation failed: Missing job URL for '{job.title}'.")
            return False
        return True

    def health_check(self) -> Dict[str, Any]:
        """
        Tests connectivity or assesses platform access restrictions.
        Returns a dict: {'healthy': bool, 'status_code': Optional[int], 'message': str, 'method': str}.
        """
        return {
            "healthy": True,
            "status_code": 200,
            "message": "Source operational",
            "method": "Standard Interface",
        }

    def get_source_status(self) -> PlatformSourceStatus:
        """
        Generates structured status for UI dashboards and health metrics.
        """
        health = self.health_check()
        return PlatformSourceStatus(
            name=self.source_name,
            platform_key=self.platform_key,
            connection_status="Connected" if health.get("healthy") else "Restricted / Manual Only",
            last_successful_fetch=utc_now_iso(),
            jobs_retrieved=0,
            new_jobs_found=0,
            errors_or_warnings=None if health.get("healthy") else health.get("message"),
            auth_requirements="None",
            permitted_method=health.get("method", "Public API / Feed"),
        )


# Alias for compatibility
JobSource = BaseJobSource

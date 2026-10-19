from typing import Any, Dict, List, Optional, Tuple

from jobpilot.config import settings
from jobpilot.logger import logger
from jobpilot.models.schemas import Job, PlatformSourceStatus, TARGET_SEARCH_QUERIES
from jobpilot.sources.arbeitnow import ArbeitnowSource
from jobpilot.sources.base import BaseJobSource, JobSource
from jobpilot.sources.csv_importer import MultiPlatformCSVImporter
from jobpilot.sources.custom_importer import CustomJobImporter
from jobpilot.sources.cutshort import CutshortAdapter
from jobpilot.sources.deduplicator import JobDeduplicator
from jobpilot.sources.demo_data import DemoJobSource
from jobpilot.sources.foundit import FounditAdapter
from jobpilot.sources.greenhouse import GreenhouseSource
from jobpilot.sources.indeed import IndeedAdapter
from jobpilot.sources.internshala import InternshalaAdapter
from jobpilot.sources.lever import LeverSource
from jobpilot.sources.linkedin import LinkedInAdapter
from jobpilot.sources.naukri import NaukriAdapter
from jobpilot.sources.wellfound import WellfoundAdapter


class JobDiscoveryService:
    """
    Unified Orchestrator across multi-platform job sources:
    - Company Careers & Verified Live Feeds: Greenhouse, Lever, Arbeitnow
    - Restricted Platforms & Manual Ingestion Adapters: Naukri, LinkedIn, Indeed, Internshala, Wellfound, Cutshort, Foundit
    - Bulk CSV & Manual Ingestion
    - Curated Demo Seeds
    """

    def __init__(self, use_demo: Optional[bool] = None):
        self.use_demo = settings.DEMO_MODE if use_demo is None else use_demo
        self.adapters: Dict[str, BaseJobSource] = {}

        # 1. Curated baseline if demo mode
        if self.use_demo:
            demo_src = DemoJobSource()
            self.adapters[demo_src.platform_key] = demo_src

        # 2. Live authorized ATS and public feeds
        gh = GreenhouseSource()
        self.adapters[gh.platform_key] = gh

        lever = LeverSource()
        self.adapters[lever.platform_key] = lever

        arbeit = ArbeitnowSource()
        self.adapters[arbeit.platform_key] = arbeit

        # 3. Major job board adapters with compliance boundaries
        naukri = NaukriAdapter()
        self.adapters[naukri.platform_key] = naukri

        linkedin = LinkedInAdapter()
        self.adapters[linkedin.platform_key] = linkedin

        indeed = IndeedAdapter()
        self.adapters[indeed.platform_key] = indeed

        internshala = InternshalaAdapter()
        self.adapters[internshala.platform_key] = internshala

        wellfound = WellfoundAdapter()
        self.adapters[wellfound.platform_key] = wellfound

        cutshort = CutshortAdapter()
        self.adapters[cutshort.platform_key] = cutshort

        foundit = FounditAdapter()
        self.adapters[foundit.platform_key] = foundit

    @property
    def sources(self) -> List[BaseJobSource]:
        return list(self.adapters.values())

    def get_adapter(self, platform_key: str) -> Optional[BaseJobSource]:
        return self.adapters.get(platform_key.lower())

    def discover(
        self,
        search_criteria: Optional[Dict[str, Any]] = None,
        limit_per_source: int = 25
    ) -> Tuple[List[Job], int]:
        """
        Discovers jobs from all active, authorized sources, executes deduplication,
        preserves all platform source links, and returns (unique_jobs, duplicate_count).
        """
        all_jobs: List[Job] = []
        criteria = search_criteria or {"target_queries": TARGET_SEARCH_QUERIES}

        for key, src in self.adapters.items():
            try:
                logger.info(f"Collecting jobs from source: {src.source_name} [{key}]")
                fetched = src.fetch_jobs(search_criteria=criteria, limit=limit_per_source)
                all_jobs.extend(fetched)
            except Exception as e:
                logger.error(f"Error fetching from {src.source_name}: {e}")

        # Multi-factor Deduplication with link preservation
        unique_jobs, dup_count = JobDeduplicator.deduplicate(all_jobs)
        logger.info(f"Discovered {len(all_jobs)} raw jobs, {len(unique_jobs)} unique ({dup_count} duplicates unified).")
        return unique_jobs, dup_count

    def get_platform_statuses(self) -> List[PlatformSourceStatus]:
        """
        Gathers live connection status and compliance diagnostics across all integrated platforms.
        """
        statuses: List[PlatformSourceStatus] = []
        for src in self.adapters.values():
            try:
                st = src.get_source_status()
                statuses.append(st)
            except Exception as e:
                logger.error(f"Failed to check status for {src.source_name}: {e}")
                statuses.append(
                    PlatformSourceStatus(
                        name=src.source_name,
                        platform_key=src.platform_key,
                        connection_status="Error",
                        errors_or_warnings=str(e),
                        auth_requirements="Unknown",
                        permitted_method="Diagnostic Failed",
                    )
                )
        return statuses

    def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Runs health check on all adapters.
        """
        results = {}
        for key, src in self.adapters.items():
            try:
                results[key] = src.health_check()
            except Exception as e:
                results[key] = {"healthy": False, "message": str(e)}
        return results


__all__ = [
    "ArbeitnowSource",
    "BaseJobSource",
    "CustomJobImporter",
    "CutshortAdapter",
    "DemoJobSource",
    "FounditAdapter",
    "GreenhouseSource",
    "IndeedAdapter",
    "InternshalaAdapter",
    "JobDeduplicator",
    "JobDiscoveryService",
    "JobSource",
    "LeverSource",
    "LinkedInAdapter",
    "MultiPlatformCSVImporter",
    "NaukriAdapter",
    "WellfoundAdapter",
]

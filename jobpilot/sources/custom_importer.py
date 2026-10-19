from typing import Any, Dict, List, Optional
from jobpilot.models.schemas import Job
from jobpilot.sources.deduplicator import (
    clean_html_text,
    extract_experience_requirements,
    extract_skills_from_text,
    generate_job_id,
)
from jobpilot.utils.date_utils import utc_now_iso


class CustomJobImporter:
    """Imports user-provided job listings via URL or pasted description."""

    @staticmethod
    def create_from_manual_input(
        title: str,
        company: str,
        description: str,
        location: str = "Pune / Remote",
        is_remote: bool = False,
        url: str = "",
        salary_range: Optional[str] = None,
        employment_type: str = "Full-time",
        source_name: str = "User Imported",
    ) -> Job:
        cleaned_desc = clean_html_text(description)
        skills = extract_skills_from_text(cleaned_desc)
        min_exp, max_exp = extract_experience_requirements(cleaned_desc)

        effective_url = url.strip() or f"https://manual-entry.local/job/{title.lower().replace(' ', '-')}"
        workplace_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in location.lower() else "On-site")

        stable_id = generate_job_id(
            source_name=source_name.lower(),
            source_id=None,
            url=effective_url,
            title=title,
            company=company,
        )

        return Job(
            id=stable_id,
            title=title.strip(),
            company=company.strip(),
            location=location.strip(),
            is_remote=is_remote,
            workplace_type=workplace_type,
            employment_type=employment_type,
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            required_skills=skills[:8],
            preferred_skills=skills[8:],
            description=cleaned_desc,
            posted_date=utc_now_iso()[:10],
            salary_range=salary_range,
            url=effective_url,
            source_name=source_name,
            source_id="manual",
            alternate_source_urls={source_name: effective_url} if url.strip() else {},
            first_discovered_at=utc_now_iso(),
            last_checked_at=utc_now_iso(),
            last_verified_at=utc_now_iso(),
            listing_status="Active",
            is_active=True,
            is_demo=False,
        )

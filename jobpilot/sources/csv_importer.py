import csv
import io
from typing import Any, Dict, List, Optional, Tuple

from jobpilot.logger import logger
from jobpilot.models.schemas import Job
from jobpilot.sources.deduplicator import (
    clean_html_text,
    extract_experience_requirements,
    extract_skills_from_text,
    generate_job_id,
)
from jobpilot.utils.date_utils import utc_now_iso


class MultiPlatformCSVImporter:
    """
    Universal CSV / TSV importer for bulk ingesting job listings from any platform:
    Naukri, LinkedIn, Indeed, Internshala, Wellfound, Cutshort, Foundit, or custom spreadsheets.
    """

    COLUMN_MAPPINGS = {
        "title": ["title", "job_title", "job title", "role", "position", "designation"],
        "company": ["company", "company_name", "company name", "employer", "organization"],
        "location": ["location", "city", "place", "job_location", "work_location"],
        "description": ["description", "job_description", "job description", "details", "summary", "jd"],
        "url": ["url", "job_url", "job url", "link", "apply_url", "application_url"],
        "source": ["source", "platform", "job_board", "source_name", "portal"],
        "experience": ["experience", "exp", "min_exp", "experience_required", "years_experience"],
        "salary": ["salary", "stipend", "compensation", "ctc", "package"],
    }

    @classmethod
    def _match_column(cls, header: str, category: str) -> bool:
        clean_header = header.strip().lower()
        candidates = cls.COLUMN_MAPPINGS.get(category, [])
        return clean_header in candidates or any(c in clean_header for c in candidates)

    @classmethod
    def import_from_csv(
        cls,
        csv_content: str,
        default_source: str = "Manual Import"
    ) -> Tuple[List[Job], int, List[str]]:
        """
        Parses CSV/TSV text and returns (imported_jobs, failed_rows, warnings).
        """
        jobs: List[Job] = []
        failed_count = 0
        warnings: List[str] = []

        try:
            # Use StringIO to parse
            f = io.StringIO(csv_content.strip())
            # Auto-detect delimiter
            sample = csv_content[:1024]
            delimiter = "\t" if "\t" in sample and sample.count("\t") > sample.count(",") else ","

            reader = csv.DictReader(f, delimiter=delimiter)
            if not reader.fieldnames:
                return [], 0, ["CSV file has no headers."]

            # Find matching column names
            col_map: Dict[str, str] = {}
            for field in reader.fieldnames:
                for cat in cls.COLUMN_MAPPINGS:
                    if cat not in col_map and cls._match_column(field, cat):
                        col_map[cat] = field

            logger.info(f"Detected CSV column mapping: {col_map}")

            row_idx = 1
            for row in reader:
                row_idx += 1
                try:
                    title = (row.get(col_map.get("title", "")) or "").strip()
                    company = (row.get(col_map.get("company", "")) or "").strip()
                    desc = clean_html_text(row.get(col_map.get("description", "")) or "")
                    if not desc:
                        desc = f"{title} opportunity at {company}"

                    if not title or not company:
                        failed_count += 1
                        continue

                    location = (row.get(col_map.get("location", "")) or "Pune / Remote").strip()
                    url = (row.get(col_map.get("url", "")) or "").strip()
                    source_val = (row.get(col_map.get("source", "")) or default_source).strip() or default_source
                    salary = (row.get(col_map.get("salary", "")) or "").strip() or None

                    is_remote = any(k in location.lower() or k in desc.lower() for k in ["remote", "work from home", "virtual"])
                    workplace_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in location.lower() else "On-site")

                    # Experience
                    exp_raw = (row.get(col_map.get("experience", "")) or "").strip()
                    if exp_raw:
                        min_e, max_e = extract_experience_requirements(f"{exp_raw} years experience")
                    else:
                        min_e, max_e = extract_experience_requirements(desc)

                    skills = extract_skills_from_text(desc)
                    emp_type = "Internship" if "intern" in title.lower() or "intern" in desc.lower() else "Full-time"

                    effective_url = url or f"https://import.jobpilot.local/{source_val.lower()}/{title.lower().replace(' ', '-')}"
                    stable_id = generate_job_id(
                        source_name=source_val.lower(),
                        source_id=None,
                        url=effective_url,
                        title=title,
                        company=company,
                    )

                    job = Job(
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
                        posted_date=utc_now_iso()[:10],
                        salary_range=salary,
                        url=effective_url,
                        source_name=source_val,
                        source_id=None,
                        alternate_source_urls={source_val: effective_url} if url else {},
                        first_discovered_at=utc_now_iso(),
                        last_checked_at=utc_now_iso(),
                        last_verified_at=utc_now_iso(),
                        listing_status="Active",
                        is_active=True,
                        is_demo=False,
                    )
                    jobs.append(job)

                except Exception as row_err:
                    failed_count += 1
                    logger.debug(f"Error parsing CSV row {row_idx}: {row_err}")

        except Exception as e:
            warnings.append(f"Failed to parse CSV file: {str(e)}")

        return jobs, failed_count, warnings

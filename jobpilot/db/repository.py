import json
from typing import Any, Dict, List, Optional, Tuple

from jobpilot.db.database import DatabaseManager, db_manager
from jobpilot.logger import logger
from jobpilot.models.schemas import (
    ApplicationDraft,
    ApplicationRecord,
    ApplicationStatus,
    AutomationRun,
    CandidateProfile,
    Job,
    MatchResult,
)
from jobpilot.utils.date_utils import utc_now_iso


class JobPilotRepository:
    def __init__(self, manager: DatabaseManager = db_manager):
        self.db = manager

    # ==========================
    # Candidate Profile
    # ==========================
    def get_candidate_profile(self) -> CandidateProfile:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM candidate_profiles ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                # Seed default profile for Rahul Girase
                profile = CandidateProfile()
                self.save_candidate_profile(profile)
                return profile

            return CandidateProfile(
                id=row["id"],
                name=row["name"],
                email=row["email"],
                phone=row["phone"],
                education=row["education"],
                graduation_year=row["graduation_year"],
                experience_level=row["experience_level"],
                max_experience_years=row["max_experience_years"],
                preferred_roles=json.loads(row["preferred_roles_json"]),
                skills=json.loads(row["skills_json"]),
                projects=json.loads(row["projects_json"]),
                preferred_locations=json.loads(row["preferred_locations_json"]),
                open_to_remote=bool(row["open_to_remote"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def save_candidate_profile(self, profile: CandidateProfile) -> None:
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM candidate_profiles ORDER BY id ASC LIMIT 1")
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    """
                    UPDATE candidate_profiles
                    SET name=?, email=?, phone=?, education=?, graduation_year=?,
                        experience_level=?, max_experience_years=?,
                        preferred_roles_json=?, skills_json=?, projects_json=?,
                        preferred_locations_json=?, open_to_remote=?, updated_at=?
                    WHERE id=?
                    """,
                    (
                        profile.name,
                        profile.email,
                        profile.phone,
                        profile.education,
                        profile.graduation_year,
                        profile.experience_level,
                        profile.max_experience_years,
                        json.dumps(profile.preferred_roles),
                        json.dumps(profile.skills),
                        json.dumps(profile.projects),
                        json.dumps(profile.preferred_locations),
                        1 if profile.open_to_remote else 0,
                        now,
                        row["id"],
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO candidate_profiles (
                        name, email, phone, education, graduation_year,
                        experience_level, max_experience_years,
                        preferred_roles_json, skills_json, projects_json,
                        preferred_locations_json, open_to_remote, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        profile.name,
                        profile.email,
                        profile.phone,
                        profile.education,
                        profile.graduation_year,
                        profile.experience_level,
                        profile.max_experience_years,
                        json.dumps(profile.preferred_roles),
                        json.dumps(profile.skills),
                        json.dumps(profile.projects),
                        json.dumps(profile.preferred_locations),
                        1 if profile.open_to_remote else 0,
                        now,
                        now,
                    ),
                )

    # ==========================
    # Job CRUD & Deduplication
    # ==========================
    def upsert_job(self, job: Job) -> bool:
        """
        Upserts job listing.
        Returns True if newly inserted, False if updated.
        Preserves existing applications and match results.
        """
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, alternate_source_urls_json FROM jobs WHERE id = ?", (job.id,))
            existing_row = cursor.fetchone()

            # Ensure current primary URL is present in alternate_source_urls
            alt_urls = dict(job.alternate_source_urls or {})
            if job.url and job.source_name:
                alt_urls[job.source_name] = job.url

            if existing_row:
                try:
                    prior_alts = json.loads(existing_row["alternate_source_urls_json"] or "{}")
                    prior_alts.update(alt_urls)
                    alt_urls = prior_alts
                except Exception:
                    pass

                cursor.execute(
                    """
                    UPDATE jobs
                    SET title=?, company=?, location=?, is_remote=?, workplace_type=?, employment_type=?,
                        min_experience_years=?, max_experience_years=?,
                        required_skills_json=?, preferred_skills_json=?,
                        description=?, posted_date=?, salary_range=?, url=?,
                        source_name=?, source_id=?, alternate_source_urls_json=?,
                        last_checked_at=?, last_verified_at=?, listing_status=?, is_active=?, is_demo=?
                    WHERE id=?
                    """,
                    (
                        job.title,
                        job.company,
                        job.location,
                        1 if job.is_remote else 0,
                        job.workplace_type,
                        job.employment_type,
                        job.min_experience_years,
                        job.max_experience_years,
                        json.dumps(job.required_skills),
                        json.dumps(job.preferred_skills),
                        job.description,
                        job.posted_date,
                        job.salary_range,
                        job.url,
                        job.source_name,
                        job.source_id,
                        json.dumps(alt_urls),
                        now,
                        job.last_verified_at or now,
                        job.listing_status,
                        1 if job.is_active else 0,
                        1 if job.is_demo else 0,
                        job.id,
                    ),
                )
                return False
            else:
                cursor.execute(
                    """
                    INSERT INTO jobs (
                        id, title, company, location, is_remote, workplace_type, employment_type,
                        min_experience_years, max_experience_years,
                        required_skills_json, preferred_skills_json,
                        description, posted_date, salary_range, url,
                        source_name, source_id, alternate_source_urls_json,
                        first_discovered_at, last_checked_at, last_verified_at, listing_status, is_active, is_demo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job.id,
                        job.title,
                        job.company,
                        job.location,
                        1 if job.is_remote else 0,
                        job.workplace_type,
                        job.employment_type,
                        job.min_experience_years,
                        job.max_experience_years,
                        json.dumps(job.required_skills),
                        json.dumps(job.preferred_skills),
                        job.description,
                        job.posted_date,
                        job.salary_range,
                        job.url,
                        job.source_name,
                        job.source_id,
                        json.dumps(alt_urls),
                        job.first_discovered_at or now,
                        now,
                        job.last_verified_at or now,
                        job.listing_status,
                        1 if job.is_active else 0,
                        1 if job.is_demo else 0,
                    ),
                )
                # Auto-initialize application record in DISCOVERED state if not exists
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO applications (job_id, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (job.id, ApplicationStatus.DISCOVERED.value, now, now),
                )
                return True

    def get_job(self, job_id: str) -> Optional[Job]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

    def _row_to_job(self, row: Any) -> Job:
        try:
            alt_urls = json.loads(row["alternate_source_urls_json"] or "{}")
        except Exception:
            alt_urls = {}
        if not alt_urls and row["url"]:
            alt_urls = {row["source_name"]: row["url"]}

        keys = row.keys() if hasattr(row, "keys") else []
        workplace_type = row["workplace_type"] if "workplace_type" in keys and row["workplace_type"] else ("Remote" if row["is_remote"] else "On-site")
        listing_status = row["listing_status"] if "listing_status" in keys and row["listing_status"] else "Active"
        last_verified = row["last_verified_at"] if "last_verified_at" in keys else None

        return Job(
            id=row["id"],
            title=row["title"],
            company=row["company"],
            location=row["location"],
            is_remote=bool(row["is_remote"]),
            workplace_type=workplace_type,
            employment_type=row["employment_type"],
            min_experience_years=row["min_experience_years"],
            max_experience_years=row["max_experience_years"],
            required_skills=json.loads(row["required_skills_json"] or "[]"),
            preferred_skills=json.loads(row["preferred_skills_json"] or "[]"),
            description=row["description"],
            posted_date=row["posted_date"],
            salary_range=row["salary_range"],
            url=row["url"],
            source_name=row["source_name"],
            source_id=row["source_id"],
            alternate_source_urls=alt_urls,
            first_discovered_at=row["first_discovered_at"],
            last_checked_at=row["last_checked_at"],
            last_verified_at=last_verified,
            listing_status=listing_status,
            is_active=bool(row["is_active"]),
            is_demo=bool(row["is_demo"]),
        )

    def list_jobs(
        self,
        keyword: Optional[str] = None,
        source: Optional[str] = None,
        is_remote: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Job]:
        query = "SELECT * FROM jobs WHERE is_active = 1"
        params: List[Any] = []

        if keyword:
            query += " AND (title LIKE ? OR company LIKE ? OR description LIKE ?)"
            pat = f"%{keyword}%"
            params.extend([pat, pat, pat])
        if source:
            query += " AND source_name = ?"
            params.append(source)
        if is_remote is not None:
            query += " AND is_remote = ?"
            params.append(1 if is_remote else 0)

        query += " ORDER BY first_discovered_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_job(r) for r in cursor.fetchall()]

    def count_jobs(self) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
            return cursor.fetchone()[0]

    # ==========================
    # Match Results
    # ==========================
    def upsert_match_result(self, match: MatchResult) -> None:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO match_results (
                    job_id, overall_score, skill_score, role_score,
                    eligibility_score, location_score, freshness_score,
                    matched_skills_json, missing_skills_json, is_eligible,
                    eligibility_reasons_json, explanation, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    overall_score=excluded.overall_score,
                    skill_score=excluded.skill_score,
                    role_score=excluded.role_score,
                    eligibility_score=excluded.eligibility_score,
                    location_score=excluded.location_score,
                    freshness_score=excluded.freshness_score,
                    matched_skills_json=excluded.matched_skills_json,
                    missing_skills_json=excluded.missing_skills_json,
                    is_eligible=excluded.is_eligible,
                    eligibility_reasons_json=excluded.eligibility_reasons_json,
                    explanation=excluded.explanation,
                    evaluated_at=excluded.evaluated_at
                """,
                (
                    match.job_id,
                    match.overall_score,
                    match.skill_score,
                    match.role_score,
                    match.eligibility_score,
                    match.location_score,
                    match.freshness_score,
                    json.dumps(match.matched_skills),
                    json.dumps(match.missing_skills),
                    1 if match.is_eligible else 0,
                    json.dumps(match.eligibility_reasons),
                    match.explanation,
                    match.evaluated_at,
                ),
            )

    def get_match_result(self, job_id: str) -> Optional[MatchResult]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM match_results WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return MatchResult(
                job_id=row["job_id"],
                overall_score=row["overall_score"],
                skill_score=row["skill_score"],
                role_score=row["role_score"],
                eligibility_score=row["eligibility_score"],
                location_score=row["location_score"],
                freshness_score=row["freshness_score"],
                matched_skills=json.loads(row["matched_skills_json"] or "[]"),
                missing_skills=json.loads(row["missing_skills_json"] or "[]"),
                is_eligible=bool(row["is_eligible"]),
                eligibility_reasons=json.loads(row["eligibility_reasons_json"] or "[]"),
                explanation=row["explanation"],
                evaluated_at=row["evaluated_at"],
            )

    def list_matched_jobs(
        self,
        min_score: float = 0.0,
        only_eligible: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Tuple[Job, MatchResult]]:
        query = """
            SELECT j.*, m.job_id, m.overall_score, m.skill_score, m.role_score,
                   m.eligibility_score, m.location_score, m.freshness_score,
                   m.matched_skills_json, m.missing_skills_json, m.is_eligible,
                   m.eligibility_reasons_json, m.explanation, m.evaluated_at
            FROM jobs j
            JOIN match_results m ON j.id = m.job_id
            WHERE j.is_active = 1 AND m.overall_score >= ?
        """
        params: List[Any] = [min_score]
        if only_eligible:
            query += " AND m.is_eligible = 1"

        query += " ORDER BY m.overall_score DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                job = self._row_to_job(row)
                match = MatchResult(
                    job_id=job.id,
                    overall_score=row["overall_score"],
                    skill_score=row["skill_score"],
                    role_score=row["role_score"],
                    eligibility_score=row["eligibility_score"],
                    location_score=row["location_score"],
                    freshness_score=row["freshness_score"],
                    matched_skills=json.loads(row["matched_skills_json"] or "[]"),
                    missing_skills=json.loads(row["missing_skills_json"] or "[]"),
                    is_eligible=bool(row["is_eligible"]),
                    eligibility_reasons=json.loads(row["eligibility_reasons_json"] or "[]"),
                    explanation=row["explanation"],
                    evaluated_at=row["evaluated_at"],
                )
                results.append((job, match))
            return results

    # ==========================
    # Application Drafts
    # ==========================
    def upsert_draft(self, draft: ApplicationDraft) -> None:
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO application_drafts (
                    job_id, resume_id, cover_letter, answers_json, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    resume_id=excluded.resume_id,
                    cover_letter=excluded.cover_letter,
                    answers_json=excluded.answers_json,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
                """,
                (
                    draft.job_id,
                    draft.resume_id,
                    draft.cover_letter,
                    json.dumps(draft.answers),
                    draft.notes,
                    draft.created_at or now,
                    now,
                ),
            )

    def get_draft(self, job_id: str) -> Optional[ApplicationDraft]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM application_drafts WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ApplicationDraft(
                job_id=row["job_id"],
                resume_id=row["resume_id"],
                cover_letter=row["cover_letter"],
                answers=json.loads(row["answers_json"] or "{}"),
                notes=row["notes"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    # ==========================
    # Application Tracking & Approval
    # ==========================
    def get_application(self, job_id: str) -> Optional[ApplicationRecord]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return ApplicationRecord(
                id=row["id"],
                job_id=row["job_id"],
                status=ApplicationStatus(row["status"]),
                submission_channel=row["submission_channel"],
                submission_notes=row["submission_notes"],
                submitted_at=row["submitted_at"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def update_application_status(
        self,
        job_id: str,
        status: ApplicationStatus,
        notes: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> None:
        now = utc_now_iso()
        submitted_at = now if status == ApplicationStatus.SUBMITTED else None

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO applications (job_id, status, submission_channel, submission_notes, submitted_at, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status=excluded.status,
                    submission_channel=COALESCE(excluded.submission_channel, applications.submission_channel),
                    submission_notes=COALESCE(excluded.submission_notes, applications.submission_notes),
                    submitted_at=COALESCE(excluded.submitted_at, applications.submitted_at),
                    updated_at=excluded.updated_at
                """,
                (
                    job_id,
                    status.value,
                    channel,
                    notes,
                    submitted_at,
                    now,
                    now,
                ),
            )
            # Log approval event
            cursor.execute(
                """
                INSERT INTO approval_events (job_id, action, user_notes, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (job_id, status.value, notes, now),
            )

    def list_applications_by_status(
        self, status: Optional[ApplicationStatus] = None
    ) -> List[Tuple[Job, ApplicationRecord, Optional[MatchResult], Optional[ApplicationDraft]]]:
        query = """
            SELECT j.*, a.id as app_id, a.status as app_status, a.submission_channel,
                   a.submission_notes, a.submitted_at, a.created_at as app_created, a.updated_at as app_updated,
                   m.overall_score, m.skill_score, m.role_score, m.eligibility_score,
                   m.location_score, m.freshness_score, m.matched_skills_json, m.missing_skills_json,
                   m.is_eligible, m.eligibility_reasons_json, m.explanation, m.evaluated_at,
                   d.cover_letter, d.answers_json, d.notes as draft_notes, d.created_at as draft_created, d.updated_at as draft_updated
            FROM applications a
            JOIN jobs j ON a.job_id = j.id
            LEFT JOIN match_results m ON j.id = m.job_id
            LEFT JOIN application_drafts d ON j.id = d.job_id
            WHERE 1=1
        """
        params: List[Any] = []
        if status:
            query += " AND a.status = ?"
            params.append(status.value)

        query += " ORDER BY a.updated_at DESC"

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                job = self._row_to_job(row)
                app = ApplicationRecord(
                    id=row["app_id"],
                    job_id=row["id"],
                    status=ApplicationStatus(row["app_status"]),
                    submission_channel=row["submission_channel"],
                    submission_notes=row["submission_notes"],
                    submitted_at=row["submitted_at"],
                    created_at=row["app_created"],
                    updated_at=row["app_updated"],
                )
                match = None
                if row["overall_score"] is not None:
                    match = MatchResult(
                        job_id=row["id"],
                        overall_score=row["overall_score"],
                        skill_score=row["skill_score"],
                        role_score=row["role_score"],
                        eligibility_score=row["eligibility_score"],
                        location_score=row["location_score"],
                        freshness_score=row["freshness_score"],
                        matched_skills=json.loads(row["matched_skills_json"] or "[]"),
                        missing_skills=json.loads(row["missing_skills_json"] or "[]"),
                        is_eligible=bool(row["is_eligible"]),
                        eligibility_reasons=json.loads(row["eligibility_reasons_json"] or "[]"),
                        explanation=row["explanation"],
                        evaluated_at=row["evaluated_at"],
                    )
                draft = None
                if row["cover_letter"] is not None:
                    draft = ApplicationDraft(
                        job_id=row["id"],
                        cover_letter=row["cover_letter"],
                        answers=json.loads(row["answers_json"] or "{}"),
                        notes=row["draft_notes"],
                        created_at=row["draft_created"],
                        updated_at=row["draft_updated"],
                    )
                results.append((job, app, match, draft))
            return results

    # ==========================
    # Resumes
    # ==========================
    def save_resume(
        self,
        filename: str,
        file_path: str,
        extracted_text: str,
        skills: List[str],
        projects: List[str],
        version_tag: Optional[str] = None,
    ) -> int:
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Set older resumes to inactive
            cursor.execute("UPDATE resumes SET is_active = 0")
            cursor.execute(
                """
                INSERT INTO resumes (
                    filename, file_path, extracted_text, parsed_skills_json,
                    parsed_projects_json, version_tag, is_active, uploaded_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    filename,
                    file_path,
                    extracted_text,
                    json.dumps(skills),
                    json.dumps(projects),
                    version_tag or "v1.0",
                    now,
                ),
            )
            return cursor.lastrowid

    def get_active_resume(self) -> Optional[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM resumes WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "filename": row["filename"],
                "file_path": row["file_path"],
                "extracted_text": row["extracted_text"],
                "parsed_skills": json.loads(row["parsed_skills_json"] or "[]"),
                "parsed_projects": json.loads(row["parsed_projects_json"] or "[]"),
                "version_tag": row["version_tag"],
                "uploaded_at": row["uploaded_at"],
            }

    # ==========================
    # Automation Runs & Logs
    # ==========================
    def record_automation_run(self, run: AutomationRun) -> int:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO automation_runs (
                    run_timestamp, status, jobs_collected, jobs_deduplicated,
                    eligible_jobs, drafts_created, errors, duration_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_timestamp,
                    run.status,
                    run.jobs_collected,
                    run.jobs_deduplicated,
                    run.eligible_jobs,
                    run.drafts_created,
                    run.errors,
                    run.duration_seconds,
                ),
            )
            return cursor.lastrowid

    def get_latest_automation_run(self) -> Optional[AutomationRun]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM automation_runs ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return None
            return AutomationRun(
                id=row["id"],
                run_timestamp=row["run_timestamp"],
                status=row["status"],
                jobs_collected=row["jobs_collected"],
                jobs_deduplicated=row["jobs_deduplicated"],
                eligible_jobs=row["eligible_jobs"],
                drafts_created=row["drafts_created"],
                errors=row["errors"],
                duration_seconds=row["duration_seconds"],
            )

    # ==========================
    # Metrics
    # ==========================
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Returns real verified statistics from SQLite database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM jobs WHERE is_active = 1")
            total_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM match_results WHERE is_eligible = 1")
            eligible_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM match_results WHERE overall_score >= 70.0")
            high_match_jobs = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM applications WHERE status = ?", (ApplicationStatus.PENDING_REVIEW.value,))
            pending_review = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM applications WHERE status = ?", (ApplicationStatus.SUBMITTED.value,))
            submitted = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM applications WHERE status IN (?, ?)",
                (ApplicationStatus.INTERVIEW.value, ApplicationStatus.ASSESSMENT.value),
            )
            interviews_assessments = cursor.fetchone()[0]

            cursor.execute("SELECT status, COUNT(*) FROM applications GROUP BY status")
            pipeline_counts = {row[0]: row[1] for row in cursor.fetchall()}

            # Score distribution
            cursor.execute("""
                SELECT
                    CASE
                        WHEN overall_score >= 80 THEN '80-100%'
                        WHEN overall_score >= 60 THEN '60-79%'
                        WHEN overall_score >= 40 THEN '40-59%'
                        ELSE '< 40%'
                    END as score_band,
                    COUNT(*) as count
                FROM match_results
                GROUP BY score_band
            """)
            score_distribution = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                "total_jobs": total_jobs,
                "eligible_jobs": eligible_jobs,
                "high_match_jobs": high_match_jobs,
                "pending_review": pending_review,
                "submitted": submitted,
                "interviews_assessments": interviews_assessments,
                "pipeline_counts": pipeline_counts,
                "score_distribution": score_distribution,
            }

    # ==========================
    # Audit Logs
    # ==========================
    def log_audit(self, action: str, entity_type: str, entity_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_logs (action, entity_type, entity_id, details_json, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    action,
                    entity_type,
                    entity_id,
                    json.dumps(details or {}),
                    now,
                ),
            )

    def list_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
            return [
                {
                    "id": r["id"],
                    "action": r["action"],
                    "entity_type": r["entity_type"],
                    "entity_id": r["entity_id"],
                    "details": json.loads(r["details_json"] or "{}"),
                    "timestamp": r["timestamp"],
                }
                for r in cursor.fetchall()
            ]

    # ==========================
    # Notifications
    # ==========================
    def record_notification(self, title: str, message: str, category: str = "info") -> int:
        now = utc_now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO notifications (title, message, category, is_read, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (title, message, category, now),
            )
            return cursor.lastrowid or 0

    def list_notifications(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,))
            return [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "message": r["message"],
                    "category": r["category"],
                    "is_read": bool(r["is_read"]),
                    "created_at": r["created_at"],
                }
                for r in cursor.fetchall()
            ]


repository = JobPilotRepository()

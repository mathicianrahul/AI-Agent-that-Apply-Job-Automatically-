import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from jobpilot.config import settings
from jobpilot.logger import logger


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- Candidate Profiles
CREATE TABLE IF NOT EXISTS candidate_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    education TEXT NOT NULL,
    graduation_year INTEGER NOT NULL,
    experience_level TEXT NOT NULL,
    max_experience_years REAL DEFAULT 1.0,
    preferred_roles_json TEXT NOT NULL,
    skills_json TEXT NOT NULL,
    projects_json TEXT NOT NULL,
    preferred_locations_json TEXT NOT NULL,
    open_to_remote INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Resumes
CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    extracted_text TEXT NOT NULL,
    parsed_skills_json TEXT,
    parsed_projects_json TEXT,
    version_tag TEXT,
    is_active INTEGER DEFAULT 1,
    uploaded_at TEXT NOT NULL
);

-- Job Sources
CREATE TABLE IF NOT EXISTS job_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    source_type TEXT NOT NULL,
    base_url TEXT,
    is_enabled INTEGER DEFAULT 1,
    last_run_at TEXT,
    created_at TEXT NOT NULL
);

-- Jobs
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT NOT NULL,
    is_remote INTEGER DEFAULT 0,
    employment_type TEXT DEFAULT 'Full-time',
    min_experience_years REAL DEFAULT 0.0,
    max_experience_years REAL DEFAULT 1.0,
    required_skills_json TEXT,
    preferred_skills_json TEXT,
    description TEXT NOT NULL,
    posted_date TEXT,
    salary_range TEXT,
    url TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_id TEXT,
    alternate_source_urls_json TEXT DEFAULT '{}',
    first_discovered_at TEXT NOT NULL,
    last_checked_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    is_demo INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
CREATE INDEX IF NOT EXISTS idx_jobs_source_name ON jobs(source_name);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date);
CREATE INDEX IF NOT EXISTS idx_jobs_is_active ON jobs(is_active);

-- Job Skills
CREATE TABLE IF NOT EXISTS job_skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    skill TEXT NOT NULL,
    is_required INTEGER DEFAULT 1,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE(job_id, skill, is_required)
);

CREATE INDEX IF NOT EXISTS idx_job_skills_skill ON job_skills(skill);

-- Match Results
CREATE TABLE IF NOT EXISTS match_results (
    job_id TEXT PRIMARY KEY,
    overall_score REAL NOT NULL,
    skill_score REAL NOT NULL,
    role_score REAL NOT NULL,
    eligibility_score REAL NOT NULL,
    location_score REAL NOT NULL,
    freshness_score REAL NOT NULL,
    matched_skills_json TEXT,
    missing_skills_json TEXT,
    is_eligible INTEGER DEFAULT 1,
    eligibility_reasons_json TEXT,
    explanation TEXT,
    evaluated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_match_overall_score ON match_results(overall_score);
CREATE INDEX IF NOT EXISTS idx_match_is_eligible ON match_results(is_eligible);

-- Application Drafts
CREATE TABLE IF NOT EXISTS application_drafts (
    job_id TEXT PRIMARY KEY,
    resume_id INTEGER,
    cover_letter TEXT NOT NULL,
    answers_json TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY(resume_id) REFERENCES resumes(id) ON DELETE SET NULL
);

-- Applications Tracker
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    submission_channel TEXT,
    submission_notes TEXT,
    submitted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

-- Approval Events
CREATE TABLE IF NOT EXISTS approval_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    action TEXT NOT NULL, -- Approved, Rejected, Saved, Edited
    user_notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

-- Automation Runs
CREATE TABLE IF NOT EXISTS automation_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    jobs_collected INTEGER DEFAULT 0,
    jobs_deduplicated INTEGER DEFAULT 0,
    eligible_jobs INTEGER DEFAULT 0,
    drafts_created INTEGER DEFAULT 0,
    errors TEXT,
    duration_seconds REAL DEFAULT 0.0
);

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    category TEXT DEFAULT 'info',
    is_read INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- Audit Logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT,
    timestamp TEXT NOT NULL
);
"""


class DatabaseManager:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or settings.absolute_db_path
        self._ensure_dir()
        self.init_db()

    def _ensure_dir(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        logger.info(f"Initializing database at: {self.db_path}")
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            # Automatic column migrations for existing databases
            for col_sql in [
                "ALTER TABLE jobs ADD COLUMN alternate_source_urls_json TEXT DEFAULT '{}'",
                "ALTER TABLE jobs ADD COLUMN workplace_type TEXT DEFAULT 'On-site'",
                "ALTER TABLE jobs ADD COLUMN listing_status TEXT DEFAULT 'Active'",
                "ALTER TABLE jobs ADD COLUMN last_verified_at TEXT",
            ]:
                try:
                    conn.execute(col_sql)
                except Exception:
                    pass


db_manager = DatabaseManager()

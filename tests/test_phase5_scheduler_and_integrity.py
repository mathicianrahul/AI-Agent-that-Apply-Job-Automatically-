import os
import tempfile
from pathlib import Path
import pytest

from jobpilot.db.database import DatabaseManager
from jobpilot.db.repository import JobPilotRepository
from jobpilot.matcher.eligibility import EligibilityChecker
from jobpilot.models.schemas import ApplicationStatus, CandidateProfile, Job
from jobpilot.scheduler.daily_runner import DailyAutomationScheduler
from jobpilot.tracker.service import ApplicationTrackerService


def test_graduation_year_disqualification():
    candidate = CandidateProfile(
        name="Rahul Girase",
        graduation_year=2027,
        max_experience_years=1.0,
    )
    job_past = Job(
        id="job_past_grad",
        title="Software Engineer",
        company="OldBatch Only",
        location="Pune",
        description="Must be graduating in 2024 or earlier. 2023 batch only.",
        url="https://example.com/past",
        source_name="Demo",
    )
    is_elig, reasons, score = EligibilityChecker.check(candidate, job_past)
    assert is_elig is False
    assert any("pre-2026" in r for r in reasons)


def test_existing_status_preserved_on_rediscovery(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = Path(tf.name)

    manager = DatabaseManager(temp_path)
    repo = JobPilotRepository(manager)

    job = Job(
        id="job_status_preserve",
        title="AI Engineer",
        company="PreserveCorp",
        location="Pune",
        description="Initial posting.",
        url="https://example.com/preserve",
        source_name="Demo",
    )
    repo.upsert_job(job)

    # Candidate was invited to an Interview!
    repo.update_application_status("job_status_preserve", ApplicationStatus.INTERVIEW, notes="Round 1 scheduled")
    app_before = repo.get_application("job_status_preserve")
    assert app_before.status == ApplicationStatus.INTERVIEW

    # Next day rediscovery run occurs
    job.description = "Updated description on new crawl."
    repo.upsert_job(job)

    app_after = repo.get_application("job_status_preserve")
    # Must preserve INTERVIEW status! Must not reset to DISCOVERED!
    assert app_after.status == ApplicationStatus.INTERVIEW

    if temp_path.exists():
        try:
            os.remove(temp_path)
        except Exception:
            pass


def test_draft_editing_and_audit_log(monkeypatch):
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = Path(tf.name)

    manager = DatabaseManager(temp_path)
    repo = JobPilotRepository(manager)
    monkeypatch.setattr("jobpilot.tracker.service.repository", repo)

    job = Job(
        id="job_draft_edit",
        title="Computer Vision Intern",
        company="VisionNext",
        location="Pune",
        description="CV internship.",
        url="https://example.com/vision",
        source_name="Demo",
    )
    repo.upsert_job(job)

    tracker = ApplicationTrackerService()
    tracker.update_draft_content(
        job_id="job_draft_edit",
        cover_letter="Customized personal cover letter emphasizing MediaPipe project.",
        answers={"Why apply?": "Passionate about gesture recognition."},
        notes="Tailored for vision role",
    )

    draft = repo.get_draft("job_draft_edit")
    assert draft is not None
    assert "MediaPipe" in draft.cover_letter
    assert draft.answers["Why apply?"] == "Passionate about gesture recognition."

    # Verify audit log
    logs = repo.list_audit_logs()
    assert any(log["action"] == "draft_edited" for log in logs)

    if temp_path.exists():
        try:
            os.remove(temp_path)
        except Exception:
            pass


def test_scheduler_lifecycle():
    scheduler = DailyAutomationScheduler()
    # Test starting scheduler
    scheduler.start_scheduler(hour=9, minute=30, timezone_str="Asia/Kolkata")
    assert scheduler.is_active is True
    assert scheduler.scheduler.running is True

    # Test pause
    scheduler.pause_scheduler()
    assert scheduler.is_active is False

    # Test resume
    scheduler.resume_scheduler()
    assert scheduler.is_active is True

    # Shutdown
    scheduler.scheduler.shutdown(wait=False)

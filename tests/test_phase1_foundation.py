import os
import tempfile
from pathlib import Path
import pytest

from jobpilot.db.database import DatabaseManager
from jobpilot.db.repository import JobPilotRepository
from jobpilot.models.schemas import (
    ApplicationDraft,
    ApplicationRecord,
    ApplicationStatus,
    CandidateProfile,
    Job,
    MatchResult,
)


@pytest.fixture
def temp_repo():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_path = Path(tf.name)
    manager = DatabaseManager(temp_path)
    repo = JobPilotRepository(manager)
    yield repo
    if temp_path.exists():
        try:
            os.remove(temp_path)
        except Exception:
            pass


def test_candidate_profile_seed_and_update(temp_repo):
    profile = temp_repo.get_candidate_profile()
    assert profile.name == "Rahul Girase"
    assert profile.graduation_year == 2027
    assert "Python" in profile.skills
    assert "AI/ML Engineer" in profile.preferred_roles

    profile.phone = "+91 9999988888"
    profile.skills.append("FastAPI")
    temp_repo.save_candidate_profile(profile)

    updated = temp_repo.get_candidate_profile()
    assert updated.phone == "+91 9999988888"
    assert "FastAPI" in updated.skills


def test_job_upsert_and_deduplication(temp_repo):
    job = Job(
        id="job_hash_123",
        title="Junior ML Engineer",
        company="TechCorp India",
        location="Pune",
        is_remote=False,
        employment_type="Full-time",
        min_experience_years=0.0,
        max_experience_years=1.0,
        required_skills=["Python", "Scikit-learn"],
        description="Exciting entry level AI role in Pune.",
        url="https://example.com/jobs/123",
        source_name="Greenhouse",
    )

    is_new = temp_repo.upsert_job(job)
    assert is_new is True

    # Same job upserted again should not duplicate
    job.description = "Updated description"
    is_new2 = temp_repo.upsert_job(job)
    assert is_new2 is False

    retrieved = temp_repo.get_job("job_hash_123")
    assert retrieved is not None
    assert retrieved.description == "Updated description"
    assert temp_repo.count_jobs() == 1


def test_application_lifecycle_and_metrics(temp_repo):
    job = Job(
        id="job_hash_456",
        title="AI Intern",
        company="AI Labs",
        location="Remote",
        is_remote=True,
        required_skills=["Python", "LangChain"],
        description="Internship for graduating batch 2027.",
        url="https://example.com/jobs/456",
        source_name="Lever",
    )
    temp_repo.upsert_job(job)

    # Initial state is DISCOVERED
    app = temp_repo.get_application("job_hash_456")
    assert app.status == ApplicationStatus.DISCOVERED

    # Update to PENDING_REVIEW
    temp_repo.update_application_status("job_hash_456", ApplicationStatus.PENDING_REVIEW, notes="Draft ready")
    app2 = temp_repo.get_application("job_hash_456")
    assert app2.status == ApplicationStatus.PENDING_REVIEW

    # Check metrics
    metrics = temp_repo.get_dashboard_metrics()
    assert metrics["total_jobs"] == 1
    assert metrics["pending_review"] == 1

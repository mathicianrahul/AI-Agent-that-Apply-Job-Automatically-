import pytest
from unittest.mock import MagicMock, patch

from jobpilot.models.schemas import Job
from jobpilot.sources.custom_importer import CustomJobImporter
from jobpilot.sources.deduplicator import (
    JobDeduplicator,
    canonicalize_url,
    clean_html_text,
    extract_experience_requirements,
    extract_skills_from_text,
    generate_job_id,
)
from jobpilot.sources.demo_data import DemoJobSource
from jobpilot.sources.greenhouse import GreenhouseSource


def test_canonicalize_url():
    url1 = "https://example.com/jobs/123/?utm_source=linkedin&utm_medium=feed&ref=123"
    url2 = "https://example.com/jobs/123"
    assert canonicalize_url(url1) == canonicalize_url(url2)


def test_deterministic_job_id():
    id1 = generate_job_id("greenhouse", "456", "https://example.com/456", "ML Engineer", "Meta")
    id2 = generate_job_id("greenhouse", "456", "https://example.com/456", "ML Engineer", "Meta")
    assert id1 == id2
    assert len(id1) == 16


def test_extract_skills_from_text():
    text = "We need an engineer experienced with Python, LangGraph, FastAPI, and SQL. Knowledge of Scikit-learn is a plus."
    skills = extract_skills_from_text(text)
    assert "Python" in skills
    assert "LangGraph" in skills
    assert "FastAPI" in skills
    assert "SQL" in skills
    assert "Scikit-learn" in skills


def test_extract_experience_requirements():
    text_fresher = "Open for freshers and 2027 college graduates. No prior experience required."
    min_e, max_e = extract_experience_requirements(text_fresher)
    assert min_e == 0.0
    assert max_e == 1.0

    text_mid = "Requires 3-5 years of industry experience in AI production systems."
    min_m, max_m = extract_experience_requirements(text_mid)
    assert min_m == 3.0
    assert max_m == 5.0


def test_deduplicator():
    job1 = Job(
        id="hash_1",
        title="AI Engineer",
        company="AlphaCorp",
        location="Pune",
        description="First instance",
        url="https://example.com/1",
        source_name="Demo",
    )
    job2 = Job(
        id="hash_1",  # duplicate ID
        title="AI Engineer",
        company="AlphaCorp",
        location="Pune",
        description="Duplicate instance",
        url="https://example.com/1",
        source_name="Demo",
    )
    job3 = Job(
        id="hash_2",
        title="AI Engineer",
        company="alphacorp",  # duplicate normalized title + company
        location="Pune",
        description="Duplicate title company",
        url="https://example.com/2",
        source_name="Demo",
    )
    job4 = Job(
        id="hash_3",
        title="Data Scientist",
        company="BetaCorp",
        location="Remote",
        description="Unique job",
        url="https://example.com/3",
        source_name="Demo",
    )

    unique, dup_count = JobDeduplicator.deduplicate([job1, job2, job3, job4])
    assert len(unique) == 2
    assert dup_count == 2
    assert unique[0].company == "AlphaCorp"
    assert unique[1].company == "BetaCorp"


def test_demo_source_returns_valid_jobs():
    src = DemoJobSource()
    jobs = src.fetch_jobs(limit=10)
    assert len(jobs) >= 5
    for j in jobs:
        assert j.id is not None
        assert j.title is not None
        assert j.company is not None
        assert j.is_demo is True
        assert len(j.description) > 20


def test_custom_importer():
    job = CustomJobImporter.create_from_manual_input(
        title="ML Engineer Intern",
        company="DeepMind Pune",
        description="Internship for 2027 batch with Python, PyTorch and LangChain.",
        location="Pune",
        is_remote=False,
    )
    assert job.title == "ML Engineer Intern"
    assert job.company == "DeepMind Pune"
    assert "Python" in job.required_skills
    assert "LangChain" in job.required_skills


@patch("requests.get")
def test_greenhouse_source_mocked(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "jobs": [
            {
                "id": 9999,
                "title": "Software Engineer Intern",
                "location": {"name": "Remote, India"},
                "content": "<p>Looking for interns with <b>Python</b> and <b>SQL</b> skills.</p>",
                "absolute_url": "https://boards.greenhouse.io/canonical/jobs/9999",
                "updated_at": "2026-10-10",
            }
        ]
    }
    mock_get.return_value = mock_resp

    src = GreenhouseSource(board_tokens=["canonical"])
    jobs = src.fetch_jobs(limit=5)
    assert len(jobs) == 1
    assert jobs[0].company == "Canonical"
    assert jobs[0].is_remote is True
    assert "Python" in jobs[0].required_skills
    assert jobs[0].employment_type == "Internship"

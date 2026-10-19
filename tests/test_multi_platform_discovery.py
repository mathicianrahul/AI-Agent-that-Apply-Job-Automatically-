import os
import pytest
from jobpilot.config import settings
from jobpilot.models.schemas import CandidateProfile, Job, PlatformSourceStatus
from jobpilot.notifications.email_digest import EmailDigestService
from jobpilot.sources import (
    ArbeitnowSource,
    CustomJobImporter,
    CutshortAdapter,
    DemoJobSource,
    FounditAdapter,
    GreenhouseSource,
    IndeedAdapter,
    InternshalaAdapter,
    JobDeduplicator,
    JobDiscoveryService,
    LeverSource,
    LinkedInAdapter,
    MultiPlatformCSVImporter,
    NaukriAdapter,
    WellfoundAdapter,
)


def test_job_source_interface_and_adapters():
    """Verify all 10 adapters adhere to the common JobSource interface."""
    adapters = [
        ArbeitnowSource(),
        GreenhouseSource(),
        LeverSource(),
        NaukriAdapter(),
        LinkedInAdapter(),
        IndeedAdapter(),
        InternshalaAdapter(),
        WellfoundAdapter(),
        CutshortAdapter(),
        FounditAdapter(),
        DemoJobSource(),
    ]

    for adapter in adapters:
        assert hasattr(adapter, "source_name")
        assert hasattr(adapter, "platform_key")
        assert hasattr(adapter, "fetch_jobs")
        assert hasattr(adapter, "normalize_job")
        assert hasattr(adapter, "validate_job")
        assert hasattr(adapter, "health_check")
        assert hasattr(adapter, "get_source_status")

        health = adapter.health_check()
        assert "healthy" in health
        assert "method" in health

        status = adapter.get_source_status()
        assert isinstance(status, PlatformSourceStatus)
        assert status.name == adapter.source_name
        assert status.platform_key == adapter.platform_key


def test_naukri_adapter_url_ingestion():
    """Verify NaukriAdapter normalizes candidate-provided URLs without scraping."""
    adapter = NaukriAdapter()
    job = adapter.parse_job_url_or_text(
        url="https://www.naukri.com/job-listings-ai-ml-engineer-fresher-jid-94812",
        title="AI/ML Engineer Fresher",
        company="Infosys Limited",
        description="Looking for 2027 batch freshers with Python, NumPy, Pandas, Scikit-learn, SQL.",
        location="Pune, Maharashtra",
        salary_range="₹6,50,000 PA",
    )
    assert job.source_name == "Naukri"
    assert job.company == "Infosys Limited"
    assert job.is_active is True
    assert "Python" in job.required_skills
    assert job.source_id == "94812"
    assert job.alternate_source_urls["Naukri"] == "https://www.naukri.com/job-listings-ai-ml-engineer-fresher-jid-94812"


def test_linkedin_adapter_url_ingestion():
    """Verify LinkedInAdapter normalizes candidate-provided LinkedIn URLs."""
    adapter = LinkedInAdapter()
    job = adapter.parse_job_url_or_text(
        url="https://www.linkedin.com/jobs/view/401928374",
        title="Junior Machine Learning Engineer",
        company="Microsoft India",
        description="Entry level role for ML Engineer. Experience: 0-1 years. Python, PyTorch, LangChain.",
        location="Bangalore (Hybrid)",
    )
    assert job.source_name == "LinkedIn"
    assert job.source_id == "401928374"
    assert "Python" in job.required_skills
    assert job.alternate_source_urls["LinkedIn"] == "https://www.linkedin.com/jobs/view/401928374"


def test_indeed_adapter_normalization():
    """Verify IndeedAdapter parses viewjob URLs."""
    adapter = IndeedAdapter()
    job = adapter.parse_job_url_or_text(
        url="https://in.indeed.com/viewjob?jk=83a71f092b",
        title="Data Analyst Entry Level",
        company="Cognizant",
        description="Fresher data analyst trainee role. SQL, Pandas, Tableau.",
        location="Pune",
    )
    assert job.source_name == "Indeed"
    assert job.source_id == "83a71f092b"
    assert "SQL" in job.required_skills


def test_internshala_adapter_normalization():
    """Verify InternshalaAdapter parses student/fresher opportunities."""
    adapter = InternshalaAdapter()
    job = adapter.parse_job_url_or_text(
        url="https://internshala.com/internship/detail/aiml-intern-109283",
        title="AI/ML Intern (Batch 2027)",
        company="HyperVerge",
        description="Computer Vision & Deep Learning intern. MediaPipe, OpenCV, Python.",
        location="Remote",
        stipend="₹25,000 /month",
    )
    assert job.source_name == "Internshala"
    assert job.employment_type == "Internship"
    assert job.is_remote is True
    assert "OpenCV" in job.required_skills


def test_multi_platform_csv_importer():
    """Verify MultiPlatformCSVImporter auto-detects columns and parses bulk listings."""
    sample_csv = """Job Title,Company Name,Job Location,Job URL,Description,Experience
AI Research Intern,Adobe Labs,Bangalore,https://adobe.com/job/ai-intern,"Python, NLP, LangChain, PyTorch",0-1 years
Junior Python Developer,Persistent Systems,Pune,https://persistent.com/job/py-dev,"Python, FastAPI, SQL, Docker",0 to 1 year
"""
    jobs, failed, warnings = MultiPlatformCSVImporter.import_from_csv(sample_csv, default_source="Naukri")
    assert len(jobs) == 2
    assert failed == 0
    assert jobs[0].title == "AI Research Intern"
    assert jobs[0].company == "Adobe Labs"
    assert "Python" in jobs[0].required_skills
    assert jobs[1].title == "Junior Python Developer"
    assert jobs[1].location == "Pune"


def test_multi_platform_deduplicator_preserves_source_links():
    """Verify JobDeduplicator unifies duplicated vacancy across multiple platforms and preserves links."""
    # Same job listed on LinkedIn and Naukri
    job1 = Job(
        id="det_id_101",
        title="Machine Learning Engineer",
        company="TechCorp India",
        location="Pune",
        is_remote=False,
        employment_type="Full-time",
        min_experience_years=0.0,
        max_experience_years=1.0,
        required_skills=["Python", "SQL"],
        description="Machine Learning Engineer opening in Pune.",
        url="https://linkedin.com/jobs/view/101",
        source_name="LinkedIn",
        alternate_source_urls={"LinkedIn": "https://linkedin.com/jobs/view/101"},
    )

    job2 = Job(
        id="det_id_102",  # Different ID from Naukri
        title="Machine Learning Engineer",
        company="TechCorp India",
        location="Pune",
        is_remote=False,
        employment_type="Full-time",
        min_experience_years=0.0,
        max_experience_years=1.0,
        required_skills=["Python", "Pandas"],
        description="Machine Learning Engineer vacancy in Pune office.",
        url="https://naukri.com/job-listings-102",
        source_name="Naukri",
        alternate_source_urls={"Naukri": "https://naukri.com/job-listings-102"},
    )

    # Different job at same company (MUST NOT BE MERGED)
    job3 = Job(
        id="det_id_103",
        title="Data Analyst Trainee",
        company="TechCorp India",
        location="Pune",
        is_remote=False,
        employment_type="Full-time",
        min_experience_years=0.0,
        max_experience_years=1.0,
        required_skills=["SQL", "Tableau"],
        description="Data analyst trainee opening.",
        url="https://indeed.com/viewjob?jk=103",
        source_name="Indeed",
        alternate_source_urls={"Indeed": "https://indeed.com/viewjob?jk=103"},
    )

    unique, dup_count = JobDeduplicator.deduplicate([job1, job2, job3])

    # Exactly 2 unique jobs: ML Engineer and Data Analyst
    assert len(unique) == 2
    assert dup_count == 1

    # Verify both source links are preserved on the merged ML Engineer job!
    ml_job = [j for j in unique if j.title == "Machine Learning Engineer"][0]
    assert "LinkedIn" in ml_job.alternate_source_urls
    assert "Naukri" in ml_job.alternate_source_urls
    assert ml_job.alternate_source_urls["LinkedIn"] == "https://linkedin.com/jobs/view/101"
    assert ml_job.alternate_source_urls["Naukri"] == "https://naukri.com/job-listings-102"
    # Merged skills
    assert "Pandas" in ml_job.required_skills


def test_email_digest_generation_and_recipient(tmp_path):
    """Verify EmailDigestService builds digest for rgirase312@gmail.com and saves HTML."""
    service = EmailDigestService(output_dir=tmp_path)
    result = service.dispatch_digest()

    assert result["success"] is True
    assert result["recipient"] == "rgirase312@gmail.com"
    assert os.path.exists(result["file_path"])
    html_text = open(result["file_path"], "r", encoding="utf-8").read()
    assert "JobPilot" in html_text
    assert "Rahul Girase" in html_text
    assert "rgirase312@gmail.com" in html_text


def test_job_discovery_service_statuses():
    """Verify JobDiscoveryService aggregates platform statuses."""
    discovery = JobDiscoveryService(use_demo=True)
    statuses = discovery.get_platform_statuses()
    platform_keys = [s.platform_key for s in statuses]

    for expected in ["naukri", "linkedin", "indeed", "internshala", "wellfound", "cutshort", "foundit", "greenhouse", "lever", "arbeitnow"]:
        assert expected in platform_keys

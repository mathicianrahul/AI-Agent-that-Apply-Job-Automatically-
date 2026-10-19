from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from jobpilot.utils.date_utils import utc_now_iso


class ApplicationStatus(str, Enum):
    DISCOVERED = "Discovered"
    ELIGIBLE = "Eligible"
    DRAFTED = "Drafted"
    PENDING_REVIEW = "Pending Review"
    APPROVED = "Approved"
    SUBMITTED = "Submitted"
    ASSESSMENT = "Assessment"
    INTERVIEW = "Interview"
    OFFER = "Offer"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"
    FAILED_SUBMISSION = "Failed Submission"


class CandidateProfile(BaseModel):
    id: Optional[int] = 1
    name: str = "Rahul Girase"
    email: Optional[str] = "rgirase312@gmail.com"
    phone: Optional[str] = "+91 9876543210"
    education: str = "Final-year BE in Artificial Intelligence and Machine Learning"
    graduation_year: int = 2027
    experience_level: str = "Fresher / entry-level"
    max_experience_years: float = 1.0
    preferred_roles: List[str] = Field(default_factory=lambda: [
        "AI/ML Engineer",
        "Junior Machine Learning Engineer",
        "Data Scientist",
        "Data Analyst",
        "Generative AI Engineer",
        "LLM Application Engineer",
        "Python Developer",
        "Computer Vision Engineer",
        "AI Research Intern"
    ])
    skills: List[str] = Field(default_factory=lambda: [
        "Python", "NumPy", "Pandas", "Scikit-learn", "SQL",
        "OpenCV", "MediaPipe", "YOLO", "LangChain", "LangGraph",
        "Hugging Face", "Flask", "FastAPI", "HTML", "CSS", "JavaScript",
        "MySQL", "MongoDB"
    ])
    projects: List[Dict[str, Any]] = Field(default_factory=lambda: [
        {
            "title": "MHT-CET College Predictor",
            "description": "ML-driven college cut-off predictor based on percentile scores and reservation categories using Python and Scikit-learn.",
            "tech": ["Python", "Scikit-learn", "Pandas", "Flask"]
        },
        {
            "title": "Air Drawing System using OpenCV and MediaPipe",
            "description": "Real-time hand gesture tracking visual canvas enabling users to draw in air via webcam feed.",
            "tech": ["Python", "OpenCV", "MediaPipe", "NumPy"]
        },
        {
            "title": "LangChain Text Chatbot",
            "description": "Contextual LLM chatbot with document indexing, retrieval augmented generation, and conversational memory.",
            "tech": ["LangChain", "Hugging Face", "FastAPI", "Python"]
        }
    ])
    preferred_locations: List[str] = Field(default_factory=lambda: [
        "Pune", "Remote"
    ])
    open_to_remote: bool = True
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class Job(BaseModel):
    id: str  # Deterministic hash ID
    title: str
    company: str
    location: str
    is_remote: bool = False
    workplace_type: str = "On-site"  # Remote, Hybrid, On-site
    employment_type: str = "Full-time"  # Full-time, Internship, Contract, etc.
    min_experience_years: float = 0.0
    max_experience_years: Optional[float] = 1.0
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    description: str
    posted_date: Optional[str] = None
    salary_range: Optional[str] = None
    url: str
    source_name: str
    source_id: Optional[str] = None
    alternate_source_urls: Dict[str, str] = Field(default_factory=dict)
    first_discovered_at: str = Field(default_factory=utc_now_iso)
    last_checked_at: str = Field(default_factory=utc_now_iso)
    last_verified_at: Optional[str] = None
    listing_status: str = "Active"
    is_active: bool = True
    is_demo: bool = False


class PlatformSourceStatus(BaseModel):
    name: str
    platform_key: str
    connection_status: str  # "Connected", "Requires API Key", "Restricted / Manual Only", "Error"
    last_successful_fetch: Optional[str] = None
    jobs_retrieved: int = 0
    new_jobs_found: int = 0
    errors_or_warnings: Optional[str] = None
    auth_requirements: str = "None"
    permitted_method: str = "Public API / Feed"


TARGET_SEARCH_QUERIES: List[str] = [
    "AI/ML Engineer Fresher",
    "Machine Learning Engineer Entry Level",
    "Data Scientist Fresher",
    "Data Analyst Entry Level",
    "Generative AI Engineer",
    "LLM Application Engineer",
    "Python Developer Fresher",
    "Computer Vision Engineer",
    "AI/ML Intern",
    "Data Science Intern",
]


class MatchResult(BaseModel):
    job_id: str
    overall_score: float
    skill_score: float
    role_score: float
    eligibility_score: float
    location_score: float
    freshness_score: float
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    is_eligible: bool = True
    eligibility_reasons: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    evaluated_at: str = Field(default_factory=utc_now_iso)


class ApplicationDraft(BaseModel):
    job_id: str
    resume_id: Optional[int] = None
    cover_letter: str
    answers: Dict[str, str] = Field(default_factory=dict)
    notes: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class ApplicationRecord(BaseModel):
    id: Optional[int] = None
    job_id: str
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    submission_channel: Optional[str] = None
    submission_notes: Optional[str] = None
    submitted_at: Optional[str] = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)


class AutomationRun(BaseModel):
    id: Optional[int] = None
    run_timestamp: str = Field(default_factory=utc_now_iso)
    status: str = "completed"  # started, completed, failed
    jobs_collected: int = 0
    jobs_deduplicated: int = 0
    eligible_jobs: int = 0
    drafts_created: int = 0
    errors: Optional[str] = None
    duration_seconds: float = 0.0

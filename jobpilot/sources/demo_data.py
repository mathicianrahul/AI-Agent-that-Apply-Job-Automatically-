from typing import List
from jobpilot.models.schemas import Job
from jobpilot.sources.base import BaseJobSource
from jobpilot.sources.deduplicator import generate_job_id
from jobpilot.utils.date_utils import utc_now_iso


class DemoJobSource(BaseJobSource):
    """
    Provides curated, clearly-labeled demo job listings tailored for
    candidate profile testing (Rahul Girase - 2027 graduate / fresher).
    """

    @property
    def source_name(self) -> str:
        return "Demo / Curated Dataset"

    def fetch_jobs(
        self,
        search_criteria: Optional[dict] = None,
        limit: int = 50
    ) -> List[Job]:
        raw_items = [
            {
                "source_id": "demo_ai_ml_pune_01",
                "title": "Junior AI/ML Engineer",
                "company": "NeuralBridge Systems [DEMO]",
                "location": "Pune, Maharashtra",
                "is_remote": False,
                "employment_type": "Full-time",
                "min_experience_years": 0.0,
                "max_experience_years": 1.0,
                "required_skills": ["Python", "Scikit-learn", "NumPy", "Pandas", "SQL"],
                "preferred_skills": ["FastAPI", "Docker", "Machine Learning"],
                "description": (
                    "Looking for a passionate Junior AI/ML Engineer in Pune. "
                    "Open to 2026/2027 engineering graduates. You will build predictive models, "
                    "clean datasets with Pandas, and deploy microservices with FastAPI. "
                    "Hands-on experience with scikit-learn and relational SQL required."
                ),
                "posted_date": "2026-10-10",
                "salary_range": "₹6,00,000 - ₹9,00,000 PA",
                "url": "https://example.com/careers/neuralbridge/junior-aiml-engineer",
            },
            {
                "source_id": "demo_genai_intern_02",
                "title": "Generative AI & LLM Intern",
                "company": "CognitiveSphere AI [DEMO]",
                "location": "Remote (India)",
                "is_remote": True,
                "employment_type": "Internship",
                "min_experience_years": 0.0,
                "max_experience_years": 1.0,
                "required_skills": ["Python", "LangChain", "LangGraph", "Hugging Face"],
                "preferred_skills": ["FastAPI", "MongoDB", "Generative AI"],
                "description": (
                    "6-month remote AI research internship for pre-final and final year BE students (2027 batch welcome). "
                    "Work with state-of-the-art open-source LLMs using Hugging Face and LangGraph agentic workflows. "
                    "Candidate should have strong Python foundation and prior chatbot / RAG project experience."
                ),
                "posted_date": "2026-10-12",
                "salary_range": "₹35,000 / month stipend",
                "url": "https://example.com/careers/cognitivesphere/genai-intern",
            },
            {
                "source_id": "demo_cv_pune_03",
                "title": "Computer Vision & Edge AI Intern",
                "company": "AcuVision Robotics [DEMO]",
                "location": "Pune, Maharashtra",
                "is_remote": False,
                "employment_type": "Internship",
                "min_experience_years": 0.0,
                "max_experience_years": 1.0,
                "required_skills": ["Python", "OpenCV", "MediaPipe", "YOLO"],
                "preferred_skills": ["NumPy", "Flask"],
                "description": (
                    "Join our edge robotics computer vision team in Pune. Ideal for candidates with projects in "
                    "real-time webcam gesture detection, MediaPipe landmarking, and YOLO object detection. "
                    "Graduating students in 2027 eligible with PPO opportunity."
                ),
                "posted_date": "2026-10-11",
                "salary_range": "₹30,000 / month stipend",
                "url": "https://example.com/careers/acuvision/cv-intern",
            },
            {
                "source_id": "demo_python_dev_04",
                "title": "Junior Python Developer",
                "company": "FinFlow Tech [DEMO]",
                "location": "Pune, Maharashtra",
                "is_remote": True,
                "employment_type": "Full-time",
                "min_experience_years": 0.0,
                "max_experience_years": 1.0,
                "required_skills": ["Python", "FastAPI", "SQL", "MySQL"],
                "preferred_skills": ["HTML", "CSS", "JavaScript", "Docker"],
                "description": (
                    "Entry-level Python developer role building backend services and automated pipelines. "
                    "Requirements: solid understanding of Python OOP, REST APIs using FastAPI/Flask, and SQL database queries. "
                    "Freshers graduating in 2026 or 2027 are welcome to apply."
                ),
                "posted_date": "2026-10-09",
                "salary_range": "₹5,50,000 - ₹7,50,000 PA",
                "url": "https://example.com/careers/finflow/junior-python-dev",
            },
            {
                "source_id": "demo_sr_lead_05",
                "title": "Senior Staff ML Engineer (5+ Yrs Exp)",
                "company": "Global Enterprise Cloud [DEMO]",
                "location": "Bangalore, Karnataka",
                "is_remote": False,
                "employment_type": "Full-time",
                "min_experience_years": 5.0,
                "max_experience_years": 10.0,
                "required_skills": ["PyTorch", "Kubernetes", "Distributed Systems", "C++"],
                "preferred_skills": ["GCP", "MLOps"],
                "description": (
                    "Disqualifying test role: Requires minimum 5 years of full-time industry experience "
                    "managing distributed machine learning infrastructure and multi-node training clusters. "
                    "Not open to interns or fresh graduates."
                ),
                "posted_date": "2026-10-01",
                "salary_range": "₹35,00,000 - ₹50,00,000 PA",
                "url": "https://example.com/careers/globalcloud/senior-staff-ml",
            },
            {
                "source_id": "demo_data_analyst_06",
                "title": "Data Analyst Trainee",
                "company": "Kinetix Analytics [DEMO]",
                "location": "Pune / Remote",
                "is_remote": True,
                "employment_type": "Full-time",
                "min_experience_years": 0.0,
                "max_experience_years": 1.0,
                "required_skills": ["Python", "SQL", "Pandas", "NumPy"],
                "preferred_skills": ["Tableau", "Power BI", "Data Analysis"],
                "description": (
                    "Fresher training program for analytical thinkers. Extract insights from relational SQL tables, "
                    "clean messy data using Pandas and NumPy in Python, and construct executive dashboards. "
                    "Final year 2027 students graduating soon are encouraged to apply."
                ),
                "posted_date": "2026-10-12",
                "salary_range": "₹5,00,000 - ₹6,50,000 PA",
                "url": "https://example.com/careers/kinetix/data-analyst-trainee",
            },
        ]
        return [self.normalize_job(item) for item in raw_items[:limit]]

    @property
    def platform_key(self) -> str:
        return "demo"

    def health_check(self) -> dict:
        return {
            "healthy": True,
            "status_code": 200,
            "message": "Curated dataset ready",
            "method": "Built-in Curated Test Feeds",
        }

    def normalize_job(self, item: dict) -> Job:
        is_remote = item["is_remote"]
        workplace_type = "Remote" if is_remote else "On-site"
        stable_id = generate_job_id(
            source_name="demo",
            source_id=item["source_id"],
            url=item["url"],
            title=item["title"],
            company=item["company"],
        )
        return Job(
            id=stable_id,
            title=item["title"],
            company=item["company"],
            location=item["location"],
            is_remote=is_remote,
            workplace_type=workplace_type,
            employment_type=item["employment_type"],
            min_experience_years=item["min_experience_years"],
            max_experience_years=item["max_experience_years"],
            required_skills=item["required_skills"],
            preferred_skills=item["preferred_skills"],
            description=item["description"],
            posted_date=item["posted_date"],
            salary_range=item["salary_range"],
            url=item["url"],
            source_name="Demo Mode",
            source_id=item["source_id"],
            alternate_source_urls={"Demo Mode": item["url"]},
            first_discovered_at=utc_now_iso(),
            last_checked_at=utc_now_iso(),
            last_verified_at=utc_now_iso(),
            listing_status="Active",
            is_active=True,
            is_demo=True,
        )

    def get_source_status(self):
        from jobpilot.models.schemas import PlatformSourceStatus
        return PlatformSourceStatus(
            name=self.source_name,
            platform_key=self.platform_key,
            connection_status="Connected",
            last_successful_fetch=utc_now_iso(),
            jobs_retrieved=7,
            new_jobs_found=7,
            errors_or_warnings=None,
            auth_requirements="None",
            permitted_method="Curated Seed Test Dataset",
        )

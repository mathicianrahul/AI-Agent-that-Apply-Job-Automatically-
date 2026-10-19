"""
Browser Agent Configuration — extends main settings with browser-specific config.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

from jobpilot.config import BASE_DIR, settings


class BrowserAgentConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Browser settings
    BROWSER_HEADLESS: bool = False  # Must be False for user to log in
    BROWSER_SLOW_MO: int = 800  # Milliseconds between actions (human-like)
    BROWSER_TIMEOUT: int = 60000  # Max wait time for elements (ms)
    BROWSER_VIEWPORT_WIDTH: int = 1366
    BROWSER_VIEWPORT_HEIGHT: int = 768

    # Rate limiting (respectful automation)
    ACTION_DELAY_MIN: float = 1.5  # Min seconds between actions
    ACTION_DELAY_MAX: float = 4.0  # Max seconds between actions
    PAGE_LOAD_WAIT: float = 3.0  # Wait after page load
    MAX_APPLICATIONS_PER_SESSION: int = 25  # Safety cap per run
    MAX_PAGES_TO_SCAN: int = 5  # Max search result pages

    # Application settings
    RESUME_PATH: str = str(BASE_DIR / "data" / "resumes" / "Rahul_Girase_Resume_Updated.pdf")
    CANDIDATE_NAME: str = "Rahul Girase"
    CANDIDATE_EMAIL: str = "rgirase312@gmail.com"
    CANDIDATE_PHONE: str = "+91 82619 75508"
    CANDIDATE_CURRENT_LOCATION: str = "Pune, India"
    CANDIDATE_EXPERIENCE_YEARS: float = 0.0
    CANDIDATE_NOTICE_PERIOD: str = "Immediate"
    CANDIDATE_EXPECTED_CTC: str = "As per industry standards"
    CANDIDATE_CURRENT_CTC: str = "0"  # Fresher

    # Job search preferences
    SEARCH_KEYWORDS: str = "AI ML Engineer, Data Scientist, Python Developer, Machine Learning, Data Analyst"
    SEARCH_LOCATION: str = "Pune"
    INCLUDE_REMOTE: bool = True  # Also search Remote jobs outside India
    SEARCH_EXPERIENCE: str = "0-1"  # years
    SEARCH_FRESHNESS: str = "7"  # days (last 7 days)
    AUTO_SUBMIT: bool = False  # True = auto-click submit, False = wait for user review

    # LinkedIn-specific
    LINKEDIN_EMAIL: Optional[str] = None
    LINKEDIN_PASSWORD: Optional[str] = None  # Never auto-login; user does it manually

    # Naukri-specific
    NAUKRI_EMAIL: Optional[str] = None
    NAUKRI_PASSWORD: Optional[str] = None  # Never auto-login; user does it manually

    # Session persistence
    BROWSER_STATE_DIR: str = str(BASE_DIR / "data" / "browser_state")

    @property
    def resume_file(self) -> Path:
        return Path(self.RESUME_PATH)

    @property
    def browser_state_path(self) -> Path:
        p = Path(self.BROWSER_STATE_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p


browser_config = BrowserAgentConfig()

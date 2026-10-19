from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Environment
    APP_ENV: str = "development"
    DEMO_MODE: bool = True
    DATABASE_PATH: str = "data/jobpilot.db"
    LOG_LEVEL: str = "INFO"

    # Hugging Face LLM Settings
    HF_TOKEN: Optional[str] = None
    HF_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"
    HF_BASE_URL: str = "https://api-inference.huggingface.co/v1"
    HF_TIMEOUT_SECONDS: int = 30
    HF_MAX_RETRIES: int = 3

    # Scheduler Settings
    SCHEDULER_ENABLED: bool = False
    DAILY_RUN_HOUR: int = 9
    DAILY_RUN_MINUTE: int = 0
    TIMEZONE: str = "Asia/Kolkata"

    # Matching Thresholds
    MIN_MATCH_SCORE_TO_DRAFT: float = 70.0
    AUTO_REJECT_BELOW_SCORE: float = 30.0

    # Weight Configurations (Sum = 100)
    WEIGHT_SKILL_OVERLAP: float = 40.0
    WEIGHT_ROLE_RELEVANCE: float = 25.0
    WEIGHT_ELIGIBILITY: float = 20.0
    WEIGHT_LOCATION: float = 10.0
    WEIGHT_FRESHNESS: float = 5.0

    # Email Digest Configuration
    DIGEST_RECIPIENT_EMAIL: str = "rgirase312@gmail.com"
    ENABLE_EMAIL_DIGEST: bool = True
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "JobPilot AI <jobpilot@notifications.local>"
    SMTP_USE_TLS: bool = True

    # Platform API / Feed Settings (Optional Authorized Integrations)
    NAUKRI_API_KEY: Optional[str] = None
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_ACCESS_TOKEN: Optional[str] = None
    INDEED_FEED_URL: Optional[str] = None
    GREENHOUSE_BOARDS: str = "canonical,cloudflare,gitlab"
    LEVER_COMPANIES: str = "figma,postman"

    @property
    def absolute_db_path(self) -> Path:
        db_path = Path(self.DATABASE_PATH)
        if not db_path.is_absolute():
            return BASE_DIR / db_path
        return db_path


settings = Settings()

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_AUTO_START: bool = True
    OLLAMA_START_COMMAND: str = "ollama serve"
    OLLAMA_START_TIMEOUT: int = 8

    # Slack
    SLACK_WEBHOOK_URL: str | None = None
    SLACK_MIN_SCORE: float = 0.70

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/auros.db"

    # Scheduler
    SCAN_SCHEDULE_HOURS: str = "6,12,18"
    SCAN_TIMEZONE: str = "America/Chicago"
    DISABLE_SCHEDULER: bool = False

    # Rate Limiting
    SCRAPE_DELAY_MIN: int = 5
    SCRAPE_DELAY_MAX: int = 10
    MAX_CONCURRENT_PAGES: int = 3

    # Preferences
    PREFERRED_WORK_MODE: str = "any"  # any|remote|hybrid|onsite
    MIN_SALARY_CONFIDENCE: float = 0.60

    # Security
    API_KEY: str | None = None

    # ATS Domains
    ATS_ALLOWED_DOMAINS: list[str] = [
        "greenhouse.io",
        "boards.greenhouse.io",
        "boards-api.greenhouse.io",
        "lever.co",
        "jobs.lever.co",
        "api.lever.co",
        "myworkdayjobs.com",
        "workdayjobs.com",
        "ashbyhq.com",
        "rippling.com",
        "jobs.jobvite.com",
        "smartrecruiters.com",
    ]

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:4001"]

    # Rate Limiting
    API_RATE_LIMIT_PER_MINUTE: int = 60


settings = Settings()

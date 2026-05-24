"""Application configuration via environment variables with sensible defaults.

Usage:
    from config import settings
    api_key = settings.congress_api_key
"""

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    # API keys
    congress_api_key: str = field(
        default_factory=lambda: os.environ.get("CONGRESS_API_KEY", "")
    )

    # Scraper settings
    scraper_delay_seconds: float = field(
        default_factory=lambda: float(os.environ.get("SCRAPER_DELAY_SECONDS", "1.0"))
    )
    scraper_timeout_seconds: int = field(
        default_factory=lambda: int(os.environ.get("SCRAPER_TIMEOUT_SECONDS", "30"))
    )
    scraper_max_retries: int = field(
        default_factory=lambda: int(os.environ.get("SCRAPER_MAX_RETRIES", "2"))
    )

    # Database
    database_path: str = field(
        default_factory=lambda: os.environ.get("DATABASE_PATH", "")
    )

    # Server
    cors_origins: str = field(
        default_factory=lambda: os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    )
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )

    # Scheduler
    scheduler_enabled: bool = field(
        default_factory=lambda: os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"
    )


settings = Settings()

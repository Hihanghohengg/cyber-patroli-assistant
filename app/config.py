import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Core
    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql://patrol_user:patrol_pass@localhost:5432/patrol_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WHITELISTED_USERS: str = ""
    TELEGRAM_ANALYST_GROUP_ID: str = ""

    @property
    def analyst_group_id(self) -> int | None:
        """Parse optional group chat ID."""
        if not self.TELEGRAM_ANALYST_GROUP_ID:
            return None
        try:
            return int(self.TELEGRAM_ANALYST_GROUP_ID.strip())
        except ValueError:
            return None

    # AI Service
    GEMINI_API_KEY: str = ""

    # Storage
    EVIDENCE_DIR: str = os.path.join("storage", "evidences")
    REPORTS_DIR: str = os.path.join("storage", "reports")

    # Dashboard / JWT Authentication
    DASHBOARD_SECRET_KEY: str = "dashboard-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours

    # Trending Engine
    TRENDING_REFRESH_SECONDS: int = 300  # 5 minutes
    TRENDING_WEIGHTS: dict = {
        "volume": 0.30,
        "growth": 0.30,
        "velocity": 0.15,
        "source_diversity": 0.10,
        "recency": 0.10,
        "relevance": 0.05,
    }

    @property
    def whitelisted_user_ids(self) -> List[int]:
        """Parse comma-separated whitelist into a list of Telegram user IDs."""
        if not self.TELEGRAM_WHITELISTED_USERS:
            return []
        return [int(uid.strip()) for uid in self.TELEGRAM_WHITELISTED_USERS.split(",") if uid.strip()]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

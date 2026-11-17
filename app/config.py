import os
from typing import List
from pydantic_settings import BaseSettings


_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_ROOT = os.path.dirname(_CURRENT_DIR)
_ENV_FILE = os.path.join(_APP_ROOT, ".env")


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Core
    ENV: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    SECRET_HMAC_KEY: str = "tilik_fips198_secret_key_2026_super_secure"

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

    # Local AI & Vision (TILIK 100% Local-First Engine)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    EMBEDDING_MODEL: str = "bge-m3"
    OLLAMA_TIMEOUT: int = 180
    CLASSIFICATION_MODE: str = "adaptive"  # baseline vs adaptive
    OCR_ENABLED: bool = True
    OCR_ENGINE: str = "rapidocr"  # rapidocr vs tesseract vs easyocr
    OCR_THRESHOLD_CHARS: int = 30
    TESSERACT_CMD: str = "tesseract"
    AI_CONCURRENCY: int = 1
    MAX_TRANSCRIPT_WORDS: int = 4000

    # Dashboard / JWT Authentication
    DASHBOARD_SECRET_KEY: str = "dashboard-change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours

    # Data Seeder
    AUTO_SEED_PROPOSAL_DATA: bool = False

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
        "env_file": (_ENV_FILE, ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

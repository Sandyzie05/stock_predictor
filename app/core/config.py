"""
Application configuration settings.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    SECRET_KEY: str = "change-this-in-production"

    # Database
    DATABASE_URL: str = (
        "sqlite+aiosqlite:///./stock_predictor_dev.db"
    )
    REDIS_URL: str = "redis://localhost:6379"

    # API Keys
    POLYGON_API_KEY: Optional[str] = None
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    FRED_API_KEY: Optional[str] = None
    SEC_USER_AGENT: Optional[str] = None

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # Rate Limiting
    API_RATE_LIMIT: int = 100
    API_RATE_WINDOW: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379"

    # Model Configuration
    MODEL_UPDATE_INTERVAL_HOURS: int = 24
    PREDICTION_CONFIDENCE_THRESHOLD: float = 0.6

    # Data Sources
    ENABLE_YAHOO_FINANCE: bool = True
    ENABLE_ALPHA_VANTAGE: bool = True
    ENABLE_NEWS_SENTIMENT: bool = True
    ENABLE_SEC_EDGAR: bool = True
    ENABLE_FRED_MACRO: bool = True
    ENABLE_MARKET_INTELLIGENCE: bool = True
    ENABLE_LOCAL_LLM: bool = False
    LOCAL_LLM_BASE_URL: Optional[str] = None
    LOCAL_LLM_MODEL: Optional[str] = None

    # Cache Settings
    CACHE_TTL_SECONDS: int = 300
    PREDICTION_CACHE_TTL_SECONDS: int = 3600
    QUOTE_CACHE_TTL_SECONDS: int = 60
    NEWS_CACHE_TTL_SECONDS: int = 900
    COMPANY_INFO_CACHE_TTL_SECONDS: int = 86400
    FRED_CACHE_TTL_SECONDS: int = 86400
    SEC_CACHE_TTL_SECONDS: int = 3600
    SEC_MAX_REQUESTS_PER_SECOND: int = 5
    MARKET_INTELLIGENCE_CACHE_TTL_SECONDS: int = 900

    @validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://", "sqlite://", "sqlite+aiosqlite://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL or SQLite URL")
        return v

    @validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v, values):
        """Validate secret key in production."""
        environment = values.get("ENVIRONMENT", "production")
        if environment == "production" and v == "change-this-in-production":
            raise ValueError("SECRET_KEY must be changed in production")
        return v

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

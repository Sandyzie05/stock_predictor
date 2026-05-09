"""
Tests for configuration module.
"""

import os

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


def make_dev_settings(**overrides):
    """Create settings without loading the repo .env file."""
    return Settings(
        _env_file=None,
        DEBUG=False,
        ENVIRONMENT="development",
        SECRET_KEY="change-this-in-production",
        **overrides,
    )


def test_default_settings():
    """Test default settings values."""
    settings = make_dev_settings()

    assert settings.DEBUG is False
    assert settings.ENVIRONMENT == "development"
    assert settings.SECRET_KEY == "change-this-in-production"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
    assert settings.ALGORITHM == "HS256"
    assert settings.API_RATE_LIMIT == 100
    assert settings.LOG_LEVEL == "INFO"
    assert settings.ENABLE_YAHOO_FINANCE is True
    assert settings.CACHE_TTL_SECONDS == 300


def test_database_url_validation():
    """Test database URL validation."""
    # Valid PostgreSQL URL
    settings = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db")
    assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost/db"

    # Invalid URL should raise validation error
    with pytest.raises(ValidationError) as exc_info:
        make_dev_settings(DATABASE_URL="mysql://user:pass@localhost/db")

    assert "DATABASE_URL must be a PostgreSQL or SQLite URL" in str(exc_info.value)


def test_secret_key_validation_production():
    """Test secret key validation in production."""
    # Should raise error with default key in production
    with pytest.raises(ValidationError) as exc_info:
        Settings(ENVIRONMENT="production", SECRET_KEY="change-this-in-production")

    assert "SECRET_KEY must be changed in production" in str(exc_info.value)

    # Should work with custom key in production
    settings = Settings(ENVIRONMENT="production", SECRET_KEY="custom-secret-key")
    assert settings.SECRET_KEY == "custom-secret-key"


def test_secret_key_validation_development():
    """Test secret key validation in development."""
    # Default key should work in development
    settings = Settings(
        ENVIRONMENT="development", SECRET_KEY="change-this-in-production"
    )
    assert settings.SECRET_KEY == "change-this-in-production"


def test_settings_from_environment():
    """Test loading settings from environment variables."""
    # Set environment variables
    env_vars = {
        "DEBUG": "true",
        "ENVIRONMENT": "testing",
        "SECRET_KEY": "test-secret",
        "DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test",
        "API_RATE_LIMIT": "200",
        "CACHE_TTL_SECONDS": "600",
    }

    for key, value in env_vars.items():
        os.environ[key] = value

    try:
        settings = Settings(_env_file=None)

        assert settings.DEBUG is True
        assert settings.ENVIRONMENT == "testing"
        assert settings.SECRET_KEY == "test-secret"
        assert settings.DATABASE_URL == "postgresql+asyncpg://test:test@localhost/test"
        assert settings.API_RATE_LIMIT == 200
        assert settings.CACHE_TTL_SECONDS == 600
    finally:
        # Clean up environment variables
        for key in env_vars:
            os.environ.pop(key, None)


def test_get_settings_caching():
    """Test that get_settings returns cached instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    # Should be the same instance (cached)
    assert settings1 is settings2


def test_api_keys_optional():
    """Test that API keys are optional."""
    settings = make_dev_settings()

    assert settings.POLYGON_API_KEY is None
    assert settings.ALPHA_VANTAGE_API_KEY is None
    assert settings.NEWS_API_KEY is None


def test_redis_url_format():
    """Test Redis URL format."""
    settings = make_dev_settings(REDIS_URL="redis://localhost:6379")
    assert settings.REDIS_URL == "redis://localhost:6379"

    settings = make_dev_settings(REDIS_URL="redis://localhost:6379/0")
    assert settings.REDIS_URL == "redis://localhost:6379/0"


def test_model_configuration():
    """Test model-related configuration."""
    settings = make_dev_settings()

    assert settings.MODEL_UPDATE_INTERVAL_HOURS == 24
    assert settings.PREDICTION_CONFIDENCE_THRESHOLD == 0.6


def test_data_source_toggles():
    """Test data source enable/disable flags."""
    settings = make_dev_settings()

    assert settings.ENABLE_YAHOO_FINANCE is True
    assert settings.ENABLE_ALPHA_VANTAGE is True
    assert settings.ENABLE_NEWS_SENTIMENT is True

    # Test disabling
    settings = make_dev_settings(
        ENABLE_YAHOO_FINANCE=False,
        ENABLE_ALPHA_VANTAGE=False,
        ENABLE_NEWS_SENTIMENT=False,
    )

    assert settings.ENABLE_YAHOO_FINANCE is False
    assert settings.ENABLE_ALPHA_VANTAGE is False
    assert settings.ENABLE_NEWS_SENTIMENT is False


def test_celery_configuration():
    """Test Celery-related configuration."""
    settings = make_dev_settings()

    assert settings.CELERY_BROKER_URL == "redis://localhost:6379"
    assert settings.CELERY_RESULT_BACKEND == "redis://localhost:6379"

"""Application configuration management."""

import os
from typing import List


class Settings:
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = os.getenv("APP_NAME", "RATP Live Tracker")
    app_version: str = os.getenv("APP_VERSION", "1.0.0")
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True") == "True"

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    reload: bool = os.getenv("RELOAD", "True") == "True"

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./ratp.db")

    # Redis Cache
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "True") == "True"
    cache_ttl_traffic: int = int(os.getenv("CACHE_TTL_TRAFFIC", "120"))
    cache_ttl_schedules: int = int(os.getenv("CACHE_TTL_SCHEDULES", "30"))
    cache_ttl_stations: int = int(os.getenv("CACHE_TTL_STATIONS", "86400"))

    # RATP APIs
    prim_api_url: str = os.getenv("PRIM_API_URL", "https://prim.iledefrance-mobilites.fr/marketplace")
    prim_api_key: str = os.getenv("PRIM_API_KEY", "")  # Get free key at https://prim.iledefrance-mobilites.fr
    community_api_url: str = os.getenv("COMMUNITY_API_URL", "https://api-ratp.pierre-grimaud.fr/v4")

    # Rate Limiting
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "True") == "True"
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))
    rate_limit_prim_traffic_per_day: int = int(os.getenv("RATE_LIMIT_PRIM_TRAFFIC_PER_DAY", "20000"))
    rate_limit_prim_departures_per_day: int = int(os.getenv("RATE_LIMIT_PRIM_DEPARTURES_PER_DAY", "1000"))

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")

    # Discord
    discord_webhook_enabled: bool = os.getenv("DISCORD_WEBHOOK_ENABLED", "True") == "True"
    discord_rate_limit_seconds: int = int(os.getenv("DISCORD_RATE_LIMIT_SECONDS", "60"))

    # Forecasting
    forecast_enabled: bool = os.getenv("FORECAST_ENABLED", "False") == "True"
    forecast_model_path: str = os.getenv("FORECAST_MODEL_PATH", "./models/forecast_model.pkl")

    # Security
    secret_key: str = os.getenv("SECRET_KEY", "change-this-to-a-random-secret-key-in-production")
    api_key_header: str = os.getenv("API_KEY_HEADER", "X-API-Key")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


# Global settings instance
settings = Settings()

"""Application configuration management."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "RATP Live Tracker"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./ratp.db"

    # Redis Cache
    redis_url: str = "redis://localhost:6379/0"
    cache_enabled: bool = True
    cache_ttl_traffic: int = 120
    cache_ttl_schedules: int = 30
    cache_ttl_stations: int = 86400

    # RATP APIs
    prim_api_url: str = "https://prim.iledefrance-mobilites.fr/marketplace"
    prim_api_key: str = ""
    community_api_url: str = "https://api-ratp.pierre-grimaud.fr/v4"

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_per_minute: int = 100
    rate_limit_prim_traffic_per_day: int = 20000
    rate_limit_prim_departures_per_day: int = 1000

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    cors_allow_credentials: bool = True

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Discord
    discord_webhook_enabled: bool = True
    discord_rate_limit_seconds: int = 60

    # Forecasting
    forecast_enabled: bool = False
    forecast_model_path: str = "./models/forecast_model.pkl"

    # Security
    secret_key: str = "change-this-to-a-random-secret-key-in-production"
    api_key_header: str = "X-API-Key"

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

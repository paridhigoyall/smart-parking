"""
Central application configuration.

All environment-driven settings for AirGuard AI live here. Values are read
from environment variables (or a .env file in development) using
pydantic-settings, giving us validated, typed configuration everywhere else
in the codebase.
"""
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ------------------------------------------------------------------
    # General
    # ------------------------------------------------------------------
    PROJECT_NAME: str = "AirGuard AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # ------------------------------------------------------------------
    # Security / Auth
    # ------------------------------------------------------------------
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_" + "x" * 32
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60          # 1 hour
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # ------------------------------------------------------------------
    # Database (PostgreSQL)
    # ------------------------------------------------------------------
    POSTGRES_SERVER: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "airguard"
    POSTGRES_PASSWORD: str = "airguard_password"
    POSTGRES_DB: str = "airguard_ai"
    SQLALCHEMY_DATABASE_URI: str | None = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    @classmethod
    def assemble_db_connection(cls, v, info):
        if isinstance(v, str) and v:
            return v
        values = info.data
        return (
            f"postgresql+psycopg://{values.get('POSTGRES_USER')}:"
            f"{values.get('POSTGRES_PASSWORD')}@{values.get('POSTGRES_SERVER')}:"
            f"{values.get('POSTGRES_PORT')}/{values.get('POSTGRES_DB')}"
        )

    # ------------------------------------------------------------------
    # Redis / Celery
    # ------------------------------------------------------------------
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None
    # When True, .delay() calls execute synchronously in-process instead of
    # going through a separate worker — used for tests / environments
    # without a running celery_worker container. Real deployments leave
    # this False and run `celery -A app.worker worker`.
    CELERY_TASK_ALWAYS_EAGER: bool = False

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v, info):
        if isinstance(v, str) and v:
            return v
        return f"redis://{info.data.get('REDIS_HOST', 'redis')}:{info.data.get('REDIS_PORT', 6379)}/1"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v, info):
        if isinstance(v, str) and v:
            return v
        return f"redis://{info.data.get('REDIS_HOST', 'redis')}:{info.data.get('REDIS_PORT', 6379)}/2"

    # ------------------------------------------------------------------
    # Notification delivery — Email (SMTP), SMS & Push (REST APIs)
    # ------------------------------------------------------------------
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "alerts@airguard.ai"
    SMTP_USE_TLS: bool = True

    # SMS via Twilio's REST API, called directly over HTTP so the base URL
    # can be pointed at a local mock in tests without needing the full SDK.
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None
    TWILIO_API_BASE_URL: str = "https://api.twilio.com"

    # Push via FCM HTTP v1. FCM_ACCESS_TOKEN is a short-lived OAuth2 bearer
    # token for a service account with the "Firebase Cloud Messaging API"
    # role — in production this should be refreshed periodically (e.g. by a
    # sidecar or scheduled task using the service account's private key)
    # rather than hardcoded; we accept it as a pre-obtained token here to
    # keep this service's own dependency footprint small.
    FCM_ACCESS_TOKEN: str | None = None
    FCM_PROJECT_ID: str | None = None
    FCM_API_BASE_URL: str = "https://fcm.googleapis.com"

    # Roles that receive alert notifications by default.
    ALERT_RECIPIENT_ROLES: list[str] = ["admin", "safety_officer", "factory_manager", "environmental_officer"]

    # ------------------------------------------------------------------
    # Route planning — plant map coordinates are on a 0-1000 canvas (see
    # ParkingArea.map_x/map_y). Gate defaults to the west edge, mid-height.
    # ------------------------------------------------------------------
    PLANT_GATE_X: float = 0.0
    PLANT_GATE_Y: float = 500.0
    ROUTE_HAZARD_BUFFER: float = 90.0

    # ------------------------------------------------------------------
    # Weather intelligence — external provider is optional; manual/site-
    # station ingestion always works regardless.
    # ------------------------------------------------------------------
    WEATHER_API_BASE_URL: str = "https://api.openweathermap.org"
    WEATHER_API_KEY: str | None = None
    WEATHER_SITE_LAT: float | None = None
    WEATHER_SITE_LON: float | None = None

    # ------------------------------------------------------------------
    # Computer vision — optional module (requirements-vision.txt). YOLO
    # weights are cached here on first use rather than wherever the
    # process happens to be started from.
    # ------------------------------------------------------------------
    VISION_MODEL_DIR: str = "/var/lib/airguard/vision-models"
    VISION_DETECTION_CONFIDENCE: float = 0.35
    # Above this confidence, a fire/smoke detection auto-raises an alert
    # through the same pipeline gas-threshold breaches use.
    VISION_ALERT_CONFIDENCE_THRESHOLD: float = 0.6

    # ------------------------------------------------------------------
    # Risk thresholds (ppm / µg/m³ unless noted) — used by the risk engine
    # ------------------------------------------------------------------
    THRESHOLD_CO_UNSAFE: float = 35.0
    THRESHOLD_CO2_UNSAFE: float = 5000.0
    THRESHOLD_NO2_UNSAFE: float = 5.0
    THRESHOLD_SO2_UNSAFE: float = 5.0
    THRESHOLD_NH3_UNSAFE: float = 25.0
    THRESHOLD_H2S_UNSAFE: float = 10.0
    THRESHOLD_METHANE_UNSAFE: float = 1000.0
    THRESHOLD_LPG_UNSAFE: float = 1000.0
    THRESHOLD_SMOKE_UNSAFE: float = 200.0
    THRESHOLD_PM25_UNSAFE: float = 55.0
    THRESHOLD_PM10_UNSAFE: float = 150.0

    # First superuser, auto-created on startup
    FIRST_SUPERUSER_EMAIL: str = "admin@airguard.ai"
    FIRST_SUPERUSER_PASSWORD: str = "ChangeMe123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# =============================================================================
# app/core/config.py
# Centralised settings loaded from environment variables via pydantic-settings.
# NOTE: pydantic-settings v2 JSON-decodes list/dict fields from .env before
# validators run. Use JSON array format in .env for all list fields:
#   ALLOWED_HOSTS=["localhost","127.0.0.1"]   ← correct
#   ALLOWED_HOSTS=localhost,127.0.0.1         ← will fail
# =============================================================================
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import (
    AnyHttpUrl,
    EmailStr,
    Field,
    PostgresDsn,
    RedisDsn,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "AI Video SaaS"
    APP_ENV: str = Field(default="development", pattern="^(development|staging|production)$")
    APP_DEBUG: bool = False
    APP_SECRET_KEY: str = Field(min_length=32)
    APP_VERSION: str = "0.1.0"

    # LIST FIELDS — must be JSON arrays in .env: ["a","b","c"]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # -------------------------------------------------------------------------
    # API server
    # -------------------------------------------------------------------------
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    API_WORKERS: int = 1
    API_RELOAD: bool = False

    # -------------------------------------------------------------------------
    # JWT
    # -------------------------------------------------------------------------
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "ai-video-saas"

    # -------------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------------
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "aivideosaas"
    POSTGRES_USER: str = "saas_user"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_SCHEMA: str = "public"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False
    TEST_POSTGRES_DB: str = "aivideosaas_test"

    DATABASE_URL: PostgresDsn | None = None
    TEST_DATABASE_URL: PostgresDsn | None = None

    @model_validator(mode="after")
    def assemble_database_urls(self) -> "Settings":
        if self.DATABASE_URL is None:
            self.DATABASE_URL = PostgresDsn(
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        if self.TEST_DATABASE_URL is None:
            self.TEST_DATABASE_URL = PostgresDsn(
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.TEST_POSTGRES_DB}"
            )
        return self

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_CELERY_DB: int = 1
    REDIS_CACHE_DB: int = 2
    REDIS_MAX_CONNECTIONS: int = 50

    REDIS_URL: RedisDsn | None = None
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    @model_validator(mode="after")
    def assemble_redis_urls(self) -> "Settings":
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else "@"
        base = f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}"
        if self.REDIS_URL is None:
            self.REDIS_URL = RedisDsn(f"{base}/{self.REDIS_DB}")
        if self.CELERY_BROKER_URL is None:
            self.CELERY_BROKER_URL = f"{base}/{self.REDIS_CELERY_DB}"
        if self.CELERY_RESULT_BACKEND is None:
            self.CELERY_RESULT_BACKEND = f"{base}/{self.REDIS_CELERY_DB}"
        return self

    # -------------------------------------------------------------------------
    # Celery
    # -------------------------------------------------------------------------
    CELERY_TASK_ALWAYS_EAGER: bool = False
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list[str] = ["json"]   # .env: ["json"]
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_SEND_SENT_EVENT: bool = True
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = 1
    CELERY_TASK_ACKS_LATE: bool = True
    CELERY_TASK_REJECT_ON_WORKER_LOST: bool = True
    CELERY_TASK_DEFAULT_QUEUE: str = "default"
    CELERY_TASK_MAX_RETRIES: int = 3
    CELERY_VIDEO_QUEUE: str = "video"
    CELERY_TRANSCRIPTION_QUEUE: str = "transcription"
    CELERY_TTS_QUEUE: str = "tts"

    # -------------------------------------------------------------------------
    # Ollama / Llama 3
    # -------------------------------------------------------------------------
    OLLAMA_HOST: str = "http://ollama"
    OLLAMA_PORT: int = 11434
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_TIMEOUT: int = 120
    OLLAMA_MAX_TOKENS: int = 4096
    OLLAMA_TEMPERATURE: float = 0.7
    OLLAMA_KEEP_ALIVE: str = "5m"
    OLLAMA_SYSTEM_PROMPT: str = (
        "You are a professional video script writer. "
        "Generate concise, engaging scripts."
    )

    @property
    def ollama_base_url(self) -> str:
        return f"{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"

    # -------------------------------------------------------------------------
    # Whisper
    # -------------------------------------------------------------------------
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_LANGUAGE: str = "auto"
    WHISPER_BEAM_SIZE: int = 5
    WHISPER_VAD_FILTER: bool = True

    # -------------------------------------------------------------------------
    # Piper TTS
    # -------------------------------------------------------------------------
    PIPER_EXECUTABLE: str = "/usr/local/bin/piper"
    PIPER_MODELS_DIR: str = "/app/models/piper"
    PIPER_DEFAULT_MODEL: str = "en_US-lessac-medium"
    PIPER_SAMPLE_RATE: int = 22050
    PIPER_OUTPUT_FORMAT: str = "wav"

    # -------------------------------------------------------------------------
    # FFmpeg
    # -------------------------------------------------------------------------
    FFMPEG_EXECUTABLE: str = "ffmpeg"
    FFPROBE_EXECUTABLE: str = "ffprobe"
    FFMPEG_THREADS: int = 0
    FFMPEG_PRESET: str = "medium"
    FFMPEG_VIDEO_CODEC: str = "libx264"
    FFMPEG_AUDIO_CODEC: str = "aac"
    FFMPEG_OUTPUT_FORMAT: str = "mp4"
    FFMPEG_DEFAULT_CRF: int = 23
    FFMPEG_MAX_DURATION_SECONDS: int = 3600
    FFMPEG_THUMBNAIL_SECOND: int = 5

    # -------------------------------------------------------------------------
    # File storage
    # -------------------------------------------------------------------------
    STORAGE_BACKEND: str = Field(default="local", pattern="^(local|s3)$")
    MEDIA_ROOT: str = "/app/media"
    MEDIA_URL: str = "/media/"
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_VIDEO_EXTENSIONS: list[str] = ["mp4", "mov", "avi", "mkv", "webm"]
    ALLOWED_AUDIO_EXTENSIONS: list[str] = ["mp3", "wav", "aac", "ogg", "m4a"]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    S3_ENDPOINT_URL: str = "https://s3.amazonaws.com"
    S3_BUCKET_NAME: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION: str = "us-east-1"
    S3_PRESIGNED_URL_EXPIRY: int = 3600

    # -------------------------------------------------------------------------
    # Rate limiting
    # -------------------------------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 20

    # -------------------------------------------------------------------------
    # Logging
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = Field(default="json", pattern="^(json|console)$")
    LOG_FILE: str = ""

    # -------------------------------------------------------------------------
    # Monitoring
    # -------------------------------------------------------------------------
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""

    # -------------------------------------------------------------------------
    # Email
    # -------------------------------------------------------------------------
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: EmailStr = "noreply@example.com"
    SMTP_FROM_NAME: str = "AI Video SaaS"
    SMTP_TLS: bool = True
    SMTP_ENABLED: bool = False

    # -------------------------------------------------------------------------
    # First superuser seed
    # -------------------------------------------------------------------------
    FIRST_SUPERUSER_EMAIL: EmailStr = "admin@aivideosaas.com"
    FIRST_SUPERUSER_PASSWORD: str = Field(min_length=8, default="changeme123!")
    FIRST_SUPERUSER_FULL_NAME: str = "System Admin"

    # -------------------------------------------------------------------------
    # Derived helpers
    # -------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def media_root_path(self) -> Path:
        return Path(self.MEDIA_ROOT)

    @property
    def piper_models_path(self) -> Path:
        return Path(self.PIPER_MODELS_DIR)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
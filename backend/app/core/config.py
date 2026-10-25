import logging
from typing import List, Union, Optional
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("scheduler.config")


class Settings(BaseSettings):
    PROJECT_NAME: str = "Scheduler"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development, test, staging, production
    LOG_LEVEL: str = "INFO"
    
    # Security & Tokens
    # Production deployments MUST replace this with a secure 32+ byte cryptographically generated secret.
    SECRET_KEY: str = "dev-insecure-secret-key-replace-in-production-scheduling-system"
    ENCRYPTION_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Session & Cookie Security
    SESSION_COOKIE_NAME: str = "scheduler_session"
    CSRF_COOKIE_NAME: str = "scheduler_csrf"
    COOKIE_SECURE: bool = False  # False for dev, True in HTTPS production
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: Optional[str] = None
    SESSION_EXPIRE_SECONDS: int = 86400 * 7  # 7 days
    
    # Rate Limiting
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 60
    
    # Database
    DATABASE_URL: str = "sqlite:///./scheduler.db"
    
    # AI Interpretation Integration (Optional - Phase 13)
    AI_ENABLED: bool = True
    AI_PROVIDER: str = "mock"  # disabled, mock, openai, gemini, external
    AI_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gpt-4o-mini"
    AI_BASE_URL: Optional[str] = None
    AI_TIMEOUT_SECONDS: float = 10.0
    AI_MAX_REQUEST_LENGTH: int = 2000
    AI_RATE_LIMIT_PER_MINUTE: int = 20

    # Google Calendar Integration (Optional)
    GOOGLE_CALENDAR_ENABLED: bool = False
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None
    GOOGLE_ENCRYPTION_KEY: Optional[str] = None

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:80",
        "http://localhost",
        "*"
    ]

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        extra="ignore"
    )

    @model_validator(mode="after")
    def validate_production_hardening(self) -> "Settings":
        """Validate critical security configurations for production environments."""
        env = self.ENVIRONMENT.lower()
        if env == "production":
            if self.SECRET_KEY.startswith("dev-") or len(self.SECRET_KEY) < 32:
                logger.warning(
                    "[SECURITY WARNING] Production environment detected with insecure or short SECRET_KEY! "
                    "Generate a cryptographically secure 32-byte secret key immediately."
                )
            if not self.COOKIE_SECURE:
                logger.warning(
                    "[SECURITY WARNING] Production environment should set COOKIE_SECURE=True to ensure "
                    "session cookies are only transmitted over HTTPS."
                )
            if "sqlite" in self.DATABASE_URL.lower():
                logger.warning(
                    "[CONFIGURATION NOTICE] Production environment is running on SQLite. "
                    "PostgreSQL 16 is recommended for high concurrency and institutional deployments."
                )
        return self


settings = Settings()

"""Application Configuration"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings"""

    # Project
    PROJECT_NAME: str = "Red Team SaaS"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/redteam_db"
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption
    ENCRYPTION_KEY: str = "your-encryption-key-change-in-production"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    ALLOW_CREDENTIALS: bool = True

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    # Architecture Option (A, B, C)
    ARCHITECTURE_OPTION: str = "C"

    # Phase 12 - Threat Intelligence
    NVD_API_KEY: Optional[str] = None   # Optional; improves NVD rate limit

    # SMTP (Phase 8 - Notifications)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_TLS: bool = True
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = "alerts@redteam.local"

    # Tool Executor
    TOOL_EXECUTION_TIMEOUT: int = 300   # 5 minutos por herramienta
    DOCKER_SANDBOX_ENABLED: bool = False
    PLUGIN_MARKETPLACE_ENABLED: bool = False
    ENABLE_API_GATEWAY: bool = False
    NUM_API_INTEGRATIONS: int = 0

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings"""
    return Settings()

settings = get_settings()

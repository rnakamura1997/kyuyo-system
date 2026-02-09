"""アプリケーション設定管理"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "kyuuyomeisai"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://kyuuyomeisai_app:password@localhost:5432/kyuuyomeisai"
    DATABASE_SYNC_URL: str = "postgresql://kyuuyomeisai_app:password@localhost:5432/kyuuyomeisai"

    # Security
    JWT_SECRET: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # File Storage
    FILE_STORAGE_PATH: str = "/var/kyuuyomeisai/files"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Encryption
    ENCRYPTION_KEY: str = "change-this-in-production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()

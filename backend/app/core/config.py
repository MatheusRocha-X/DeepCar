from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "DeepCar API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite+aiosqlite:///./deepcar.db"

    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 300

    SECRET_KEY: str = "deepcar-secret-key-change-in-production"
    ALGORITHM: str = "HS256"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://deepcar.app",
    ]
    CORS_ORIGIN_REGEX: Optional[str] = r"^https?://(?!(localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$).+$"

    SCRAPER_INTERVAL_MINUTES: int = 60
    MAX_PAGES_PER_SOURCE: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

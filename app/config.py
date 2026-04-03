from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/notifications"

    @computed_field
    def async_database_url(self) -> str:
        # PaaS providers (Render, Heroku) often give URLs starting with postgres:// or postgresql://
        # We must forcibly use the asyncpg driver
        url = self.database_url
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App
    app_env: str = "development"
    log_level: str = "INFO"

    # Rate limiting
    rate_limit_max: int = 100
    rate_limit_window_seconds: int = 3600

    # Worker
    worker_poll_interval: float = 0.5
    worker_batch_size: int = 10


settings = Settings()

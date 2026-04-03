from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/notifications"

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

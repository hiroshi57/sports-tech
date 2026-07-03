from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "sports-tech API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/sportstech"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery: テストでは true にして同期実行する
    CELERY_TASK_ALWAYS_EAGER: bool = False

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    AWS_REGION: str = "ap-northeast-1"
    S3_BUCKET_NAME: str = "sports-tech-videos"

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""


settings = Settings()

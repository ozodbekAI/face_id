from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    MEDIA_DIR: str = "data/media"

    # Attendance/day boundary timezone (used for "today" computations)
    COMPANY_TZ: str = "Asia/Tashkent"

    # Logging
    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"

settings = Settings()

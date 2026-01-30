from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str


    # Attendance/day boundary timezone
    COMPANY_TZ: str = "Asia/Tashkent"

    # Optional admin key for /admin endpoints. If empty, /admin is open (dev).
    ADMIN_KEY: str = ""

    # Logging
    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"


settings = Settings()

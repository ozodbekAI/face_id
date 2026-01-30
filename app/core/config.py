from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str


    AUTH_TOKEN_TTL_HOURS: int = 24

    # PBKDF2 params
    PASSWORD_PBKDF2_ITERATIONS: int = 200_000

    ROOT_ADMIN_USERNAME: str = "admin"
    ROOT_ADMIN_PASSWORD: str = ""  


    COMPANY_TZ: str = "Asia/Tashkent"

    LOG_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"


settings = Settings()

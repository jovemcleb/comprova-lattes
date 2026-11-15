from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = (
        "postgresql+psycopg://comprova_lattes:comprova_lattes@localhost:5432/comprova_lattes"
    )
    redis_url: str = "redis://localhost:6379/0"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_temperature: float = 0.0
    gemini_timeout_ms: int = Field(default=120000, ge=1000, le=300000)
    gemini_max_attempts: int = Field(default=2, ge=1, le=3)


settings = Settings()

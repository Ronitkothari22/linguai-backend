from functools import lru_cache

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    supabase_jwt_secret: str
    database_url: str
    gemini_api_key: str
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:
        missing = ", ".join(
            sorted(
                ".".join(str(part) for part in error["loc"])
                for error in exc.errors()
                if error["type"] == "missing"
            )
        )
        raise RuntimeError(
            f"Missing required environment variables: {missing or 'unknown'}"
        ) from exc

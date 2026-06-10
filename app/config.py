from functools import lru_cache
from pathlib import Path

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    database_url: str
    auth_jwt_secret: str
    gemini_api_key: str
    environment: str = "development"

    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", REPO_ROOT / ".env"),
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

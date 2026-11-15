from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.providers.model_ref import ModelRef

# Repo-root `.env`, for running the API on the host. In containers this path doesn't
# exist and compose provides the environment instead. Real env vars always win.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class ConfigError(RuntimeError):
    """Raised at startup when the environment is incomplete or invalid."""


class Settings(BaseSettings):
    """Process-wide settings, read from the environment (and `.env` for local runs).

    Only settings used by code that exists today live here; later tasks add their own
    (embeddings in M1-05, auth in M2-01, …). The full list is in `.env.example`.
    """

    model_config = SettingsConfigDict(extra="ignore", frozen=True)

    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_base_url: str = "http://localhost:8000"
    frontend_origin: str = "http://localhost:3000"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    database_url: PostgresDsn
    redis_url: RedisDsn

    # LLM providers (M1-04). Model strings are `provider:model_id` (see ModelRef).
    gemini_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"
    default_chat_model: str = "gemini:gemini-3.5-flash-lite"
    fallback_chat_model: str | None = None  # tried on quota/outage errors
    extraction_model: str | None = None  # None = default_chat_model
    judge_model: str = "gemini:gemini-3.6-flash"
    llm_timeout_s: float = Field(default=60.0, gt=0)

    @field_validator("gemini_api_key", "fallback_chat_model", "extraction_model", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        # `FOO=` in .env means "not set", not an empty string.
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("default_chat_model", "fallback_chat_model", "extraction_model", "judge_model")
    @classmethod
    def _valid_model_ref(cls, value: str | None) -> str | None:
        if value is not None:
            ModelRef.parse(value)  # raises ValueError with a readable message
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def _require_asyncpg(cls, value: PostgresDsn) -> PostgresDsn:
        if value.scheme != "postgresql+asyncpg":
            raise ValueError("must use the async driver: postgresql+asyncpg://…")
        return value


def load_settings(env_file: Path | None = ROOT_ENV_FILE) -> Settings:
    """Build settings, turning validation errors into one readable message."""
    try:
        return Settings(_env_file=env_file)
    except ValidationError as exc:
        problems = []
        for err in exc.errors():
            name = str(err["loc"][0]).upper() if err["loc"] else "?"
            reason = "is required" if err["type"] == "missing" else err["msg"]
            problems.append(f"  - {name} {reason}")
        raise ConfigError(
            "Invalid configuration (see .env.example):\n" + "\n".join(problems)
        ) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()

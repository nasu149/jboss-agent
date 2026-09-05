"""Application configuration loaded from environment variables and ``.env``."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated settings shared by every learning step.

    STEP 10-12 add durable operational paths. The earlier STEP 7 demos may still
    choose an in-memory checkpointer, but the scheduler/UI operational runtime
    deliberately uses SQLite so monitor cursors and pending approvals survive
    process restarts.
    """

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    google_api_key: SecretStr | None = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-3.5-flash", alias="GEMINI_MODEL")
    gemini_temperature: float = Field(default=1.0, ge=0.0, le=2.0, alias="GEMINI_TEMPERATURE")

    teams_webhook_url: str | None = Field(default=None, alias="TEAMS_WEBHOOK_URL")
    teams_dry_run: bool = Field(default=True, alias="TEAMS_DRY_RUN")
    teams_notify_min_severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        default="MEDIUM", alias="TEAMS_NOTIFY_MIN_SEVERITY"
    )

    poll_interval_seconds: int = Field(default=180, ge=1, alias="POLL_INTERVAL_SECONDS")
    server_id: str = Field(default="jboss-01", min_length=1, alias="SERVER_ID")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    jboss_mode: Literal["fake", "real"] = Field(default="fake", alias="JBOSS_MODE")
    jboss_mcp_transport: str = Field(default="stdio", alias="JBOSS_MCP_TRANSPORT")
    fake_jboss_data_dir: str = Field(default=".data/fake_jboss", alias="FAKE_JBOSS_DATA_DIR")

    checkpoint_backend: Literal["memory", "sqlite"] = Field(
        default="memory", alias="CHECKPOINT_BACKEND"
    )
    checkpoint_db_path: str = Field(default=".data/checkpoints.sqlite", alias="CHECKPOINT_DB_PATH")
    runtime_db_path: str = Field(default=".data/runtime.sqlite", alias="RUNTIME_DB_PATH")
    simulator_db_path: str = Field(default=".data/simulator.sqlite", alias="SIMULATOR_DB_PATH")
    evaluation_report_path: str = Field(
        default=".data/evaluation_latest.json", alias="EVALUATION_REPORT_PATH"
    )

    max_investigation_rounds: int = Field(default=5, ge=1, alias="MAX_INVESTIGATION_ROUNDS")
    max_recovery_attempts: int = Field(default=2, ge=1, alias="MAX_RECOVERY_ATTEMPTS")
    evaluation_runs: int = Field(default=12, ge=10, le=30, alias="EVALUATION_RUNS")
    evaluation_seed: int = Field(default=42, alias="EVALUATION_SEED")

    @field_validator("google_api_key", mode="before")
    @classmethod
    def empty_google_api_key_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("teams_webhook_url", mode="before")
    @classmethod
    def empty_teams_webhook_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator(
        "gemini_model",
        "server_id",
        "app_env",
        "log_level",
        "jboss_mcp_transport",
        "fake_jboss_data_dir",
        "checkpoint_db_path",
        "runtime_db_path",
        "simulator_db_path",
        "evaluation_report_path",
    )
    @classmethod
    def non_blank_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @property
    def has_google_api_key(self) -> bool:
        return self.google_api_key is not None and bool(self.google_api_key.get_secret_value().strip())

    @property
    def monitoring_thread_id(self) -> str:
        """Stable thread used by STEP 10 scheduler cursor persistence."""
        return f"monitor:{self.server_id}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

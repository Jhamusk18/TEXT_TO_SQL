"""Environment-driven settings (pydantic-settings, reads `.env` when present)."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime knobs. Every field maps 1:1 to an env var (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    default_row_limit: int = Field(default=200, ge=1)
    max_correction_rounds: int = Field(default=2, ge=0)
    statement_timeout_ms: int = Field(default=5000, ge=100)
    schema_token_budget: int = Field(default=1200, ge=100)
    sensitive_tables: str = "customers"
    history_db_path: str = "artifacts/history.sqlite"

    def sensitive_table_set(self) -> set[str]:
        return {name.strip() for name in self.sensitive_tables.split(",") if name.strip()}

    @property
    def offline_llm(self) -> bool:
        return not self.openai_api_key

    @property
    def offline_db(self) -> bool:
        return not self.database_url

"""Environment-driven settings (pydantic-settings, reads `.env` when present)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime knobs. Every field maps 1:1 to an env var (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str | None = None
    llm_provider: Literal["auto", "gemini", "openai"] = "auto"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    default_row_limit: int = Field(default=200, ge=1)
    max_correction_rounds: int = Field(default=2, ge=0)
    statement_timeout_ms: int = Field(default=5000, ge=100)
    schema_token_budget: int = Field(default=2000, ge=100)
    sample_rows_per_table: int = Field(default=3, ge=0, le=10)
    prompt_mode: Literal["schema_aware", "baseline"] = "schema_aware"
    summarize_results: bool = True
    sensitive_tables: str = "customers"
    history_db_path: str = "artifacts/history.sqlite"

    def sensitive_table_set(self) -> set[str]:
        return {name.strip() for name in self.sensitive_tables.split(",") if name.strip()}

    @property
    def active_provider(self) -> Literal["gemini", "openai", "fake"]:
        """Which LLM backend is used. ``auto`` prefers Gemini, then OpenAI, then the fake.

        An explicit ``LLM_PROVIDER`` without its API key falls back to the fake
        rather than silently using the other provider.
        """
        if self.llm_provider == "gemini":
            return "gemini" if self.gemini_api_key else "fake"
        if self.llm_provider == "openai":
            return "openai" if self.openai_api_key else "fake"
        if self.gemini_api_key:
            return "gemini"
        return "openai" if self.openai_api_key else "fake"

    @property
    def llm_model_name(self) -> str | None:
        return {"gemini": self.gemini_model, "openai": self.openai_model}.get(
            self.active_provider
        )

    @property
    def offline_llm(self) -> bool:
        return self.active_provider == "fake"

    @property
    def offline_db(self) -> bool:
        return not self.database_url

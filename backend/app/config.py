"""Application configuration using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    app_name: str = "AlgoScan"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # ── External API Keys ────────────────────────────────
    newsapi_key: str = ""
    alpha_vantage_key: str = ""

    # ── FinBERT ──────────────────────────────────────────
    finbert_model_name: str = "ProsusAI/finbert"
    finbert_batch_size: int = 32
    finbert_max_length: int = 512
    finbert_cache_size: int = 10_000

    # ── Server ───────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # ── Paths ────────────────────────────────────────────
    base_dir: Path = Path(__file__).resolve().parent.parent
    ml_artifacts_dir: Path = Path(__file__).resolve().parent.parent / "ml_artifacts"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()

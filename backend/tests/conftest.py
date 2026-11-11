"""Shared pytest fixtures for AlgoScan tests."""

from __future__ import annotations

from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.fixture
def settings() -> Settings:
    """Return test settings with dummy API keys."""
    return Settings(
        debug=True,
        newsapi_key="test_key",
        alpha_vantage_key="test_key",
        finbert_model_name="ProsusAI/finbert",
        finbert_batch_size=8,
        finbert_cache_size=100,
    )

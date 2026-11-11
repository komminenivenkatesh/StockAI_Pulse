"""Shared FastAPI dependencies."""

from __future__ import annotations

from app.config import Settings, get_settings


def get_app_settings() -> Settings:
    """FastAPI dependency returning the application settings singleton."""
    return get_settings()

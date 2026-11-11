"""Structured logging configuration for AlgoScan."""

from __future__ import annotations

import logging
import sys
from typing import Final

LOG_FORMAT: Final[str] = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with structured formatting."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers on repeated calls
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "transformers", "ccxt", "yfinance", "filelock"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for a module."""
    return logging.getLogger(f"algoscan.{name}")

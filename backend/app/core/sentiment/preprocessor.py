"""Text preprocessing and deduplication for financial headlines."""

from __future__ import annotations

import re
from typing import Final

from app.utils.logging import get_logger

logger = get_logger(__name__)

# ── Regex patterns ───────────────────────────────────────────
_URL_PATTERN: Final[re.Pattern[str]] = re.compile(r"https?://\S+")
_HTML_PATTERN: Final[re.Pattern[str]] = re.compile(r"<[^>]+>")
_SPECIAL_CHARS: Final[re.Pattern[str]] = re.compile(r"[^\w\s.,!?;:'\"-]+")
_WHITESPACE: Final[re.Pattern[str]] = re.compile(r"\s+")

# Common non-informative headline patterns
_NOISE_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"^\s*$"),                       # empty
    re.compile(r"^\[removed\]$", re.IGNORECASE),
    re.compile(r"^\[deleted\]$", re.IGNORECASE),
]

# Minimum headline length after cleaning (characters)
_MIN_LENGTH: Final[int] = 15


def clean_headline(text: str) -> str:
    """Clean a single financial headline.

    Steps:
      1. Strip HTML tags
      2. Remove URLs
      3. Remove non-standard special characters
      4. Collapse whitespace
      5. Strip leading/trailing whitespace

    Args:
        text: Raw headline string.

    Returns:
        Cleaned headline string.
    """
    text = _HTML_PATTERN.sub("", text)
    text = _URL_PATTERN.sub("", text)
    text = _SPECIAL_CHARS.sub(" ", text)
    text = _WHITESPACE.sub(" ", text)
    return text.strip()


def is_valid_headline(text: str) -> bool:
    """Check if a cleaned headline is valid for sentiment analysis."""
    if len(text) < _MIN_LENGTH:
        return False
    for pattern in _NOISE_PATTERNS:
        if pattern.match(text):
            return False
    return True


def filter_by_ticker(headline: str, ticker: str) -> bool:
    """Check if headline is relevant to the given ticker.

    Performs case-insensitive search for the ticker symbol
    or common company name variants.
    """
    headline_lower = headline.lower()
    ticker_lower = ticker.lower()

    # Direct ticker mention
    if ticker_lower in headline_lower:
        return True

    # Strip exchange suffix (e.g. 'reliance' from 'reliance.ns')
    clean_sym = ticker_lower.split('.')[0] if '.' in ticker_lower else ticker_lower
    if len(clean_sym) >= 3 and clean_sym in headline_lower:
        return True

    # Check for dollar-sign prefixed ticker (e.g., $AAPL)
    if f"${ticker_lower}" in headline_lower:
        return True

    return False


def preprocess_headlines(
    headlines: list[str],
    ticker: str | None = None,
    deduplicate: bool = True,
) -> list[str]:
    """Full preprocessing pipeline for a list of headlines.

    Args:
        headlines: Raw headline strings.
        ticker: Optional ticker to filter relevance.
        deduplicate: Whether to remove duplicate headlines.

    Returns:
        List of cleaned, valid, unique headlines.
    """
    cleaned: list[str] = []
    seen: set[str] = set()

    for raw in headlines:
        text = clean_headline(raw)

        if not is_valid_headline(text):
            continue

        if ticker and not filter_by_ticker(text, ticker):
            continue

        if deduplicate:
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)

        cleaned.append(text)

    logger.debug(
        "Preprocessed %d → %d headlines (ticker=%s).",
        len(headlines), len(cleaned), ticker,
    )
    return cleaned

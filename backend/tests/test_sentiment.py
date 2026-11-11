"""Unit tests for the sentiment analysis pipeline."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.sentiment.preprocessor import (
    clean_headline,
    filter_by_ticker,
    is_valid_headline,
    preprocess_headlines,
)
from app.core.sentiment.aggregator import (
    aggregate_sentiment,
    compute_current_sentiment,
)


# ── Preprocessor Tests ───────────────────────────────────────


class TestCleanHeadline:
    def test_removes_html_tags(self) -> None:
        assert clean_headline("<b>Apple</b> beats <i>estimates</i>") == "Apple beats estimates"

    def test_removes_urls(self) -> None:
        assert clean_headline("AAPL surges https://example.com more info") == "AAPL surges more info"

    def test_collapses_whitespace(self) -> None:
        assert clean_headline("  Apple   beats    estimates  ") == "Apple beats estimates"

    def test_removes_special_chars(self) -> None:
        result = clean_headline("Apple™ beats © estimates®")
        assert "™" not in result
        assert "©" not in result


class TestIsValidHeadline:
    def test_rejects_short_text(self) -> None:
        assert is_valid_headline("Short") is False

    def test_accepts_valid_headline(self) -> None:
        assert is_valid_headline("Apple beats earnings estimates in Q3") is True

    def test_rejects_deleted(self) -> None:
        assert is_valid_headline("[removed]") is False


class TestFilterByTicker:
    def test_finds_ticker(self) -> None:
        assert filter_by_ticker("AAPL stock price surges", "AAPL") is True

    def test_finds_dollar_ticker(self) -> None:
        assert filter_by_ticker("$AAPL is up 5%", "AAPL") is True

    def test_rejects_unrelated(self) -> None:
        assert filter_by_ticker("Oil prices drop sharply", "AAPL") is False


class TestPreprocessHeadlines:
    def test_deduplication(self) -> None:
        headlines = ["Apple beats estimates", "apple beats estimates", "Apple beats estimates"]
        result = preprocess_headlines(headlines, deduplicate=True)
        assert len(result) == 1

    def test_filters_short(self) -> None:
        headlines = ["Short", "Apple reports strong quarterly earnings growth"]
        result = preprocess_headlines(headlines)
        assert len(result) == 1

    def test_ticker_filter(self) -> None:
        headlines = [
            "Apple AAPL reports strong earnings",
            "Oil prices surge on demand",
        ]
        result = preprocess_headlines(headlines, ticker="AAPL")
        assert len(result) == 1


# ── Aggregator Tests ─────────────────────────────────────────


class TestAggregateSentiment:
    def test_empty_input(self) -> None:
        result = aggregate_sentiment([], [])
        assert result == []

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="Length mismatch"):
            aggregate_sentiment([{"compound": 0.5}], [])

    def test_produces_data_points(self) -> None:
        now = datetime.now(tz=timezone.utc)
        scores = [{"compound": 0.8}, {"compound": -0.2}, {"compound": 0.5}]
        timestamps = [now, now, now]
        result = aggregate_sentiment(scores, timestamps, window="1h")
        assert len(result) >= 1
        assert -1.0 <= result[0].compound_score <= 1.0


class TestComputeCurrentSentiment:
    def test_empty_returns_zero(self) -> None:
        assert compute_current_sentiment([], []) == 0.0

    def test_positive_scores(self) -> None:
        now = datetime.now(tz=timezone.utc)
        scores = [{"compound": 0.9}, {"compound": 0.8}]
        result = compute_current_sentiment(scores, [now, now])
        assert result > 0.0

    def test_bounded_output(self) -> None:
        now = datetime.now(tz=timezone.utc)
        scores = [{"compound": 1.0}] * 10
        result = compute_current_sentiment(scores, [now] * 10)
        assert -1.0 <= result <= 1.0

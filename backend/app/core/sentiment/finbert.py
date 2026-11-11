"""FinBERT-based financial sentiment analyzer.

Loads the ProsusAI/finbert model once at startup and provides
batched inference with LRU caching on headline hashes.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    from app.config import Settings

from app.utils.cache import LRUCache
from app.utils.errors import ModelNotLoadedError
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Label mapping for ProsusAI/finbert
_LABEL_MAP: dict[int, str] = {0: "positive", 1: "negative", 2: "neutral"}


class SentimentScore:
    """Container for a single headline's sentiment analysis result."""

    __slots__ = ("headline", "positive", "negative", "neutral", "compound", "label")

    def __init__(
        self,
        headline: str,
        positive: float,
        negative: float,
        neutral: float,
    ) -> None:
        self.headline = headline
        self.positive = positive
        self.negative = negative
        self.neutral = neutral
        self.compound = round(positive - negative, 6)
        self.label = max(
            ("positive", positive),
            ("negative", negative),
            ("neutral", neutral),
            key=lambda x: x[1],
        )[0]

    def to_dict(self) -> dict[str, object]:
        return {
            "headline": self.headline,
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral,
            "compound": self.compound,
            "label": self.label,
        }


class FinBERTAnalyzer:
    """Wrapper around the FinBERT transformer for financial sentiment.

    Usage:
        analyzer = FinBERTAnalyzer(settings)
        analyzer.load_model()           # called once at startup
        scores = analyzer.predict(["Apple beats earnings estimates."])
    """

    def __init__(self, settings: Settings) -> None:
        self._model_name = settings.finbert_model_name
        self._batch_size = settings.finbert_batch_size
        self._max_length = settings.finbert_max_length
        self._device = None

        self._tokenizer = None
        self._model = None
        self._cache: LRUCache[SentimentScore] = LRUCache(max_size=settings.finbert_cache_size)
        self._loaded = False

    # ── Lifecycle ────────────────────────────────────────────

    def load_model(self) -> None:
        """Download (if needed) and load the FinBERT model and tokenizer."""
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if self._device is None:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logger.info("Loading FinBERT model '%s' onto %s...", self._model_name, self._device)
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self._model_name)
        self._model.to(self._device)  # type: ignore[union-attr]
        self._model.eval()  # type: ignore[union-attr]
        self._loaded = True
        logger.info("FinBERT model loaded successfully.")

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ── Inference ────────────────────────────────────────────

    @staticmethod
    def _hash_text(text: str) -> str:
        """Produce a deterministic hash key for cache lookups."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def predict(self, headlines: list[str]) -> list[SentimentScore]:
        """Score a list of headlines, returning SentimentScore objects.

        Results are cached by headline hash. Batched inference is used
        for uncached headlines to maximize throughput.

        Args:
            headlines: List of financial news headlines to analyze.

        Returns:
            List of SentimentScore in the same order as input.

        Raises:
            ModelNotLoadedError: If load_model() has not been called.
        """
        if not self._loaded or self._model is None or self._tokenizer is None:
            raise ModelNotLoadedError(self._model_name)

        results: list[SentimentScore | None] = [None] * len(headlines)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        # Separate cached vs uncached
        for idx, headline in enumerate(headlines):
            key = self._hash_text(headline)
            cached = self._cache.get(key)
            if cached is not None:
                results[idx] = cached
            else:
                uncached_indices.append(idx)
                uncached_texts.append(headline)

        # Batched inference on uncached headlines
        if uncached_texts:
            scores = self._batched_inference(uncached_texts)
            for local_idx, original_idx in enumerate(uncached_indices):
                score = scores[local_idx]
                self._cache.put(self._hash_text(uncached_texts[local_idx]), score)
                results[original_idx] = score

        return results  # type: ignore[return-value]

    def _batched_inference(self, texts: list[str]) -> list[SentimentScore]:
        """Run inference in mini-batches for memory efficiency."""
        import torch
        all_scores: list[SentimentScore] = []

        for batch_start in range(0, len(texts), self._batch_size):
            batch_texts = texts[batch_start : batch_start + self._batch_size]
            encodings = self._tokenizer(  # noqa — not None here
                batch_texts,
                padding=True,
                truncation=True,
                max_length=self._max_length,
                return_tensors="pt",
            )
            encodings = {k: v.to(self._device) for k, v in encodings.items()}

            with torch.no_grad():
                outputs = self._model(**encodings)  # noqa — not None here
                probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

            for i, text in enumerate(batch_texts):
                probs = probabilities[i].cpu().tolist()
                score = SentimentScore(
                    headline=text,
                    positive=round(probs[0], 6),
                    negative=round(probs[1], 6),
                    neutral=round(probs[2], 6),
                )
                all_scores.append(score)

        return all_scores

    @property
    def cache_stats(self) -> dict[str, int]:
        """Return cache utilization stats."""
        return {
            "cached_items": len(self._cache),
            "max_size": self._cache._max_size,
        }

"""Model registry for versioning and persistence.

Manages saving, loading, and version tracking of trained ML models.
Models are stored in the ml_artifacts/ directory with metadata.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

from app.utils.logging import get_logger

logger = get_logger(__name__)

METADATA_FILE: Final[str] = "registry.json"


class ModelVersion:
    """A single model version entry."""

    def __init__(
        self,
        model_name: str,
        version: str,
        model_type: str,
        task: str,
        ticker: str,
        file_path: str,
        metrics: dict[str, Any] | None = None,
        created_at: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.version = version
        self.model_type = model_type
        self.task = task
        self.ticker = ticker
        self.file_path = file_path
        self.metrics = metrics or {}
        self.created_at = created_at or datetime.now(tz=timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "version": self.version,
            "model_type": self.model_type,
            "task": self.task,
            "ticker": self.ticker,
            "file_path": self.file_path,
            "metrics": self.metrics,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModelVersion:
        return cls(**data)


class ModelRegistry:
    """File-based model registry for versioned ML models.

    Usage:
        registry = ModelRegistry(base_dir=Path("ml_artifacts"))
        registry.register(model_version)
        latest = registry.get_latest("xgboost", "AAPL")
    """

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self._base_dir / METADATA_FILE
        self._versions: list[ModelVersion] = []
        self._load_registry()

    def register(
        self,
        model_name: str,
        model_type: str,
        task: str,
        ticker: str,
        file_path: Path,
        metrics: dict[str, Any] | None = None,
    ) -> ModelVersion:
        """Register a new model version.

        Args:
            model_name: Human-readable model name.
            model_type: Model type (e.g., 'xgboost', 'bilstm', 'ensemble').
            task: 'classification' or 'regression'.
            ticker: Ticker the model was trained for.
            file_path: Path to the saved model file.
            metrics: Training/validation metrics.

        Returns:
            The created ModelVersion.
        """
        version = self._next_version(model_type, ticker)

        entry = ModelVersion(
            model_name=model_name,
            version=version,
            model_type=model_type,
            task=task,
            ticker=ticker.upper(),
            file_path=str(file_path),
            metrics=metrics,
        )

        self._versions.append(entry)
        self._save_registry()

        logger.info(
            "Registered model: %s v%s (type=%s, ticker=%s)",
            model_name, version, model_type, ticker,
        )
        return entry

    def get_latest(
        self, model_type: str, ticker: str
    ) -> ModelVersion | None:
        """Get the latest version of a model for a ticker."""
        matches = [
            v for v in self._versions
            if v.model_type == model_type and v.ticker == ticker.upper()
        ]
        if not matches:
            return None
        return matches[-1]

    def get_all(
        self, model_type: str | None = None, ticker: str | None = None
    ) -> list[ModelVersion]:
        """Get all model versions, optionally filtered."""
        results = self._versions
        if model_type:
            results = [v for v in results if v.model_type == model_type]
        if ticker:
            results = [v for v in results if v.ticker == ticker.upper()]
        return results

    def delete(
        self, model_type: str, ticker: str, version: str
    ) -> bool:
        """Delete a specific model version."""
        for i, v in enumerate(self._versions):
            if (
                v.model_type == model_type
                and v.ticker == ticker.upper()
                and v.version == version
            ):
                # Remove file
                file_path = Path(v.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info("Deleted model file: %s", file_path)

                self._versions.pop(i)
                self._save_registry()
                return True
        return False

    def get_model_dir(self, model_type: str, ticker: str) -> Path:
        """Get the directory for a model type and ticker."""
        model_dir = self._base_dir / model_type / ticker.upper()
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir

    def _next_version(self, model_type: str, ticker: str) -> str:
        """Generate the next version string."""
        existing = self.get_all(model_type, ticker)
        if not existing:
            return "v1"
        latest_num = max(
            int(v.version.lstrip("v")) for v in existing
        )
        return f"v{latest_num + 1}"

    def _load_registry(self) -> None:
        """Load the registry from disk."""
        if self._registry_path.exists():
            try:
                with open(self._registry_path, "r") as f:
                    data = json.load(f)
                self._versions = [
                    ModelVersion.from_dict(entry) for entry in data
                ]
                logger.debug("Loaded %d model versions from registry.", len(self._versions))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("Failed to load registry: %s", exc)
                self._versions = []

    def _save_registry(self) -> None:
        """Persist the registry to disk."""
        with open(self._registry_path, "w") as f:
            json.dump(
                [v.to_dict() for v in self._versions],
                f,
                indent=2,
            )

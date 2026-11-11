"""Custom exception hierarchy for AlgoScan."""

from __future__ import annotations


class AlgoScanError(Exception):
    """Base exception for all AlgoScan errors."""

    def __init__(self, message: str = "An unexpected error occurred.", status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ExternalAPIError(AlgoScanError):
    """Raised when an external API call fails."""

    def __init__(self, service: str, detail: str = "") -> None:
        msg = f"External API error [{service}]: {detail}" if detail else f"External API error [{service}]"
        super().__init__(message=msg, status_code=502)
        self.service = service


class ModelNotLoadedError(AlgoScanError):
    """Raised when the ML model has not been loaded yet."""

    def __init__(self, model_name: str = "unknown") -> None:
        super().__init__(message=f"Model '{model_name}' is not loaded.", status_code=503)
        self.model_name = model_name


class TickerNotFoundError(AlgoScanError):
    """Raised when a ticker symbol cannot be resolved."""

    def __init__(self, ticker: str) -> None:
        super().__init__(message=f"Ticker '{ticker}' not found.", status_code=404)
        self.ticker = ticker


class InsufficientDataError(AlgoScanError):
    """Raised when there is not enough data to perform an operation."""

    def __init__(self, detail: str = "Insufficient data.") -> None:
        super().__init__(message=detail, status_code=422)

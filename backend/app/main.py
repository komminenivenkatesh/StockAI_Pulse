"""AlgoScan — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.config import get_settings
from app.core.sentiment.finbert import FinBERTAnalyzer
from app.utils.errors import AlgoScanError
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: load models on startup, clean up on shutdown."""
    settings = get_settings()
    setup_logging(level=logging.DEBUG if settings.debug else logging.INFO)
    logger.info("Starting %s...", settings.app_name)

    # Lazy-load FinBERT: create analyzer but don't download model at startup
    analyzer = FinBERTAnalyzer(settings=settings)
    app.state.finbert = analyzer
    app.state.finbert_loaded = False
    logger.info("FinBERT analyzer initialized (model will load on first use).")

    yield

    # Cleanup
    logger.info("Shutting down %s.", settings.app_name)


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Predictive algorithmic trading & sentiment analysis platform.",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_origin_regex=r"https?://.*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(AlgoScanError)
    async def algoscan_error_handler(request: Request, exc: AlgoScanError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "message": exc.message},
        )

    # Health check
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    # Mount routers
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()

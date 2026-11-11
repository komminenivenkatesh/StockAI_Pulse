from fastapi import APIRouter
from .v1 import sentiment as sentiment_router
from .v1 import market as market_router
from .v1 import forecast as forecast_router
from .v1 import backtest as backtest_router
from .v1 import risk as risk_router

router = APIRouter()
api_router = router  # Alias for backward compatibility with main.py

router.include_router(sentiment_router.router, prefix="/sentiment", tags=["sentiment"])
router.include_router(market_router.router, prefix="/market", tags=["market"])
router.include_router(forecast_router.router, prefix="/forecast", tags=["forecast"])
router.include_router(backtest_router.router, prefix="/backtest", tags=["backtest"])
router.include_router(risk_router.router, prefix="/risk", tags=["risk"])


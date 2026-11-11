import logging
import time
from fastapi import APIRouter, HTTPException
from typing import Any, List
from ...models.backtest import (
    BacktestRequest,
    BacktestResponse,
    StrategyListResponse,
    StrategyInfo,
    StrategyParamInfo,
    BacktestDataPayload,
    EquityPoint,
    TradeRecord,
)
from ...models.risk import RiskMetrics
from ...core.market.data_fetcher import MarketDataFetcher
from ...core.market.indicators import add_all_indicators
from ...core.backtest.strategies import generate_signals, STRATEGY_CATALOG
from ...core.backtest.engine import BacktestEngine
from ...core.backtest.reporting import format_backtest_report

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/run", response_model=BacktestResponse)
async def run_backtest(request: BacktestRequest):
    """
    Run an algorithmic strategy backtest on historical OHLCV data.
    """
    start_time = time.time()
    try:
        fetcher = MarketDataFetcher()
        market_result = await fetcher.fetch(
            ticker=request.ticker,
            period=request.period,
            interval=request.interval,
        )
        
        if market_result.is_empty or len(market_result.df) < 10:
            raise HTTPException(
                status_code=422,
                detail=f"Insufficient data for ticker {request.ticker} ({len(market_result.df)} bars found)",
            )

        df = market_result.df.copy()
        df = add_all_indicators(df)

        strategy_name = request.strategy.upper()
        if strategy_name not in STRATEGY_CATALOG:
            matched = False
            for k in STRATEGY_CATALOG:
                if k.lower() == request.strategy.lower():
                    strategy_name = k
                    matched = True
                    break
            if not matched:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown strategy '{request.strategy}'. Supported strategies: {list(STRATEGY_CATALOG.keys())}",
                )

        signals = generate_signals(df, strategy_name, request.params)

        engine = BacktestEngine()
        result = engine.run(
            df=df,
            signals=signals,
            initial_capital=request.initial_capital,
            commission_pct=request.commission_pct,
            slippage_pct=request.slippage_pct,
        )

        report = format_backtest_report(result, request.ticker, strategy_name)

        metrics_dict = report["metrics"]
        risk_metrics = RiskMetrics(
            total_roi=metrics_dict.get("total_roi", 0.0),
            annualized_roi=metrics_dict.get("annualized_roi", 0.0),
            sharpe_ratio=metrics_dict.get("sharpe_ratio", 0.0),
            sortino_ratio=metrics_dict.get("sortino_ratio", 0.0),
            max_drawdown=metrics_dict.get("max_drawdown", 0.0),
            calmar_ratio=metrics_dict.get("calmar_ratio", 0.0),
            win_rate=metrics_dict.get("win_rate", 0.0),
            profit_factor=metrics_dict.get("profit_factor", 0.0),
            total_trades=metrics_dict.get("total_trades", 0),
            winning_trades=metrics_dict.get("winning_trades", 0),
            losing_trades=metrics_dict.get("losing_trades", 0),
            avg_trade_return=metrics_dict.get("avg_trade_return", 0.0),
            volatility_annualized=metrics_dict.get("volatility_annualized", 0.0),
        )

        equity_points = [
            EquityPoint(
                timestamp=str(p["timestamp"]),
                equity=float(p["equity"]),
                benchmark=float(p["benchmark"]),
                drawdown=float(p["drawdown"]),
            )
            for p in report["equity_curve"]
        ]

        trade_records = [
            TradeRecord(
                entry_time=str(t["entry_time"]),
                exit_time=str(t["exit_time"]),
                entry_price=float(t["entry_price"]),
                exit_price=float(t["exit_price"]),
                side=str(t["side"]),
                pnl=float(t["pnl"]),
                return_pct=float(t["return_pct"]),
                duration_bars=int(t["duration_bars"]),
            )
            for t in report["trades"]
        ]

        data_payload = BacktestDataPayload(
            ticker=request.ticker.upper(),
            strategy=strategy_name,
            metrics=risk_metrics,
            equity_curve=equity_points,
            trades=trade_records,
            monthly_returns=report["monthly_returns"],
        )

        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return BacktestResponse(
            status="ok",
            data=data_payload,
            meta={
                "execution_time_ms": elapsed_ms,
                "ticker": request.ticker.upper(),
                "bars": len(df),
                "strategy": strategy_name,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Backtest error for {request.ticker}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")

@router.get("/strategies", response_model=StrategyListResponse)
async def get_strategies():
    """
    Get available backtesting strategies with dynamic parameter definitions from STRATEGY_CATALOG.
    """
    try:
        strategies_list: List[StrategyInfo] = []
        for name, spec in STRATEGY_CATALOG.items():
            params: List[StrategyParamInfo] = []
            for p_name, p_spec in spec.get("params", {}).items():
                params.append(
                    StrategyParamInfo(
                        name=p_name,
                        type=str(p_spec.get("type", "any")),
                        default=p_spec.get("default"),
                        description=f"Default {p_spec.get('default')} (range: {p_spec.get('min', 'N/A')} - {p_spec.get('max', 'N/A')})",
                    )
                )
            strategies_list.append(
                StrategyInfo(
                    name=name,
                    description=spec.get("description", ""),
                    parameters=params,
                )
            )
        return StrategyListResponse(status="ok", data=strategies_list)
    except Exception as e:
        logger.error(f"Get strategies error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


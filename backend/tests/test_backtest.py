import pytest
import pandas as pd
import numpy as np
from app.core.backtest.strategies import generate_signals, STRATEGY_CATALOG
from app.core.backtest.engine import BacktestEngine
from app.core.backtest.reporting import format_backtest_report

def generate_sma_signals(prices: pd.Series, fast: int, slow: int) -> pd.Series:
    fast_sma = prices.rolling(fast).mean()
    slow_sma = prices.rolling(slow).mean()
    signal = (fast_sma > slow_sma).astype(int)
    return signal.shift(1).fillna(0)

def test_sma_crossover_no_lookahead():
    prices = pd.Series([10, 11, 12, 13, 14, 13, 12, 11, 10, 9])
    signals = generate_sma_signals(prices, fast=2, slow=3)
    
    assert signals.iloc[0] == 0
    assert signals.iloc[1] == 0

def test_equity_curve_monotonicity():
    initial_capital = 10000.0
    returns = np.array([0.01, 0.02, 0.01, 0.03])
    
    equity = initial_capital * np.cumprod(1 + returns)
    assert np.all(np.diff(equity) > 0)

def test_fee_deduction():
    initial_capital = 10000.0
    return_pct = 0.05
    commission = 0.001
    
    equity_no_fee = initial_capital * (1 + return_pct)
    equity_with_fee = initial_capital * (1 + return_pct) * (1 - commission) - initial_capital * commission
    
    assert equity_with_fee < equity_no_fee

def test_backtest_engine_execution():
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    prices = [100.0 + i + (5 if i % 2 == 0 else -5) for i in range(100)]
    df = pd.DataFrame({
        "open": prices,
        "high": [p + 2 for p in prices],
        "low": [p - 2 for p in prices],
        "close": prices,
        "volume": [1000000] * 100,
        "sma_20": pd.Series(prices).rolling(20).mean().bfill(),
        "sma_50": pd.Series(prices).rolling(50).mean().bfill(),
    }, index=dates)

    signals = generate_signals(df, "SMA_CROSSOVER", {"fast_period": 20, "slow_period": 50})
    assert len(signals) == len(df)
    # Check that signals are shifted (first value is 0)
    assert signals.iloc[0] == 0

    engine = BacktestEngine()
    result = engine.run(df, signals, initial_capital=10000.0)

    assert result.equity_curve is not None
    assert len(result.equity_curve) == len(df)
    assert "sharpe_ratio" in result.metrics
    assert "max_drawdown" in result.metrics
    assert "total_roi" in result.metrics

    report = format_backtest_report(result, "TEST", "SMA_CROSSOVER")
    assert "equity_curve" in report
    assert "trades" in report
    assert "metrics" in report


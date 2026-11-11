import numpy as np
import pandas as pd
from typing import Any, List, Optional, Union
import math
import logging

logger = logging.getLogger(__name__)

def calculate_cumulative_returns(returns: pd.Series) -> pd.Series:
    """Calculates the cumulative compounded return series."""
    if returns.empty:
        return pd.Series(dtype=float)
    return (1 + returns).cumprod() - 1.0

def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02, periods_per_year: int = 252) -> float:
    """Calculates the annualized Sharpe ratio."""
    if returns.empty:
        return 0.0
    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    excess_returns = returns - rf_per_period
    std = excess_returns.std()
    if pd.isna(std) or std == 0:
        return 0.0
    return float(excess_returns.mean() / std * np.sqrt(periods_per_year))

def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02, periods_per_year: int = 252) -> float:
    """Calculates the annualized Sortino ratio (downside deviation based)."""
    if returns.empty:
        return 0.0
    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1
    excess_returns = returns - rf_per_period
    downside_returns = excess_returns[excess_returns < 0]
    std_downside = downside_returns.std()
    if pd.isna(std_downside) or std_downside == 0:
        return 0.0
    return float(excess_returns.mean() / std_downside * np.sqrt(periods_per_year))

def calculate_max_drawdown(equity_curve: pd.Series) -> tuple[float, pd.Series]:
    """Calculates the max drawdown and drawdown series."""
    if equity_curve.empty:
        return 0.0, pd.Series(dtype=float)
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max
    drawdown = drawdown.fillna(0.0)
    max_drawdown = float(drawdown.min())
    return abs(max_drawdown), drawdown

def calculate_win_rate(trade_returns: Union[List[float], pd.Series]) -> float:
    """Calculates the percentage of trades with a positive return."""
    if isinstance(trade_returns, list):
        trade_returns = pd.Series(trade_returns)
    if trade_returns.empty:
        return 0.0
    wins = (trade_returns > 0).sum()
    return float(wins / len(trade_returns))

def calculate_profit_factor(trade_returns: Union[List[float], pd.Series]) -> float:
    """Calculates the profit factor (gross profits / gross losses)."""
    if isinstance(trade_returns, list):
        trade_returns = pd.Series(trade_returns)
    if trade_returns.empty:
        return 0.0
    gross_profits = trade_returns[trade_returns > 0].sum()
    gross_losses = abs(trade_returns[trade_returns < 0].sum())
    if gross_losses == 0:
        return float("inf") if gross_profits > 0 else 0.0
    return float(gross_profits / gross_losses)

def calculate_calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
    """Calculates the Calmar ratio (annualized return / max drawdown)."""
    if max_drawdown == 0 or pd.isna(max_drawdown):
        return 0.0
    return float(annualized_return / abs(max_drawdown))

def calculate_all_risk_metrics(
    returns: pd.Series, 
    equity_curve: pd.Series, 
    trade_returns: Optional[Union[List[float], pd.Series]] = None, 
    risk_free_rate: float = 0.02, 
    periods_per_year: int = 252,
    benchmark_returns: Optional[pd.Series] = None
) -> dict[str, Any]:
    """Calculates a comprehensive metrics bundle."""
    if returns.empty or equity_curve.empty:
        return {}

    total_roi = float((equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0) if len(equity_curve) > 0 else 0.0
    
    n_periods = len(returns)
    if n_periods > 0:
        annualized_roi = (1 + total_roi) ** (periods_per_year / n_periods) - 1.0
    else:
        annualized_roi = 0.0

    benchmark_roi = None
    if benchmark_returns is not None and not benchmark_returns.empty:
        benchmark_equity = (1 + benchmark_returns).cumprod()
        if len(benchmark_equity) > 0:
            benchmark_roi = float(benchmark_equity.iloc[-1] - 1.0)
            
    sharpe_ratio = calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)
    sortino_ratio = calculate_sortino_ratio(returns, risk_free_rate, periods_per_year)
    max_drawdown_val, _ = calculate_max_drawdown(equity_curve)
    calmar_ratio = calculate_calmar_ratio(annualized_roi, max_drawdown_val)
    
    volatility_annualized = float(returns.std() * np.sqrt(periods_per_year)) if not returns.empty else 0.0

    win_rate = 0.0
    profit_factor = 0.0
    total_trades = 0
    winning_trades = 0
    losing_trades = 0
    avg_trade_return = 0.0

    if trade_returns is not None:
        if isinstance(trade_returns, list):
            trade_returns = pd.Series(trade_returns)
        total_trades = len(trade_returns)
        if total_trades > 0:
            win_rate = calculate_win_rate(trade_returns)
            profit_factor = calculate_profit_factor(trade_returns)
            winning_trades = int((trade_returns > 0).sum())
            losing_trades = int((trade_returns <= 0).sum())
            avg_trade_return = float(trade_returns.mean())

    return {
        "total_roi": total_roi,
        "annualized_roi": annualized_roi,
        "benchmark_roi": benchmark_roi,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown_val,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "avg_trade_return": avg_trade_return,
        "volatility_annualized": volatility_annualized
    }

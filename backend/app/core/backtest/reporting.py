import pandas as pd
from typing import Dict, Any, List
from .engine import BacktestResult

def format_backtest_report(result: BacktestResult, ticker: str, strategy_name: str) -> Dict[str, Any]:
    """
    Serializes backtest outputs into frontend-friendly JSON structures.
    """
    
    equity_curve_data: List[Dict[str, Any]] = []
    
    df_curve = pd.DataFrame({
        'equity': result.equity_curve,
        'benchmark': result.benchmark_equity,
        'drawdown': result.drawdown_series
    })
    
    for date, row in df_curve.iterrows():
        equity_curve_data.append({
            "timestamp": date.isoformat() if hasattr(date, 'isoformat') else str(date),
            "equity": float(row['equity']) if pd.notna(row['equity']) else 0.0,
            "benchmark": float(row['benchmark']) if pd.notna(row['benchmark']) else 0.0,
            "drawdown": float(row['drawdown']) if pd.notna(row['drawdown']) else 0.0
        })

    trades_data: List[Dict[str, Any]] = []
    for t in result.trades:
        trades_data.append({
            "entry_time": t.entry_time.isoformat() if hasattr(t.entry_time, 'isoformat') else str(t.entry_time),
            "exit_time": t.exit_time.isoformat() if hasattr(t.exit_time, 'isoformat') else str(t.exit_time),
            "entry_price": float(t.entry_price),
            "exit_price": float(t.exit_price),
            "size": float(t.size),
            "side": str(t.side),
            "pnl": float(t.pnl),
            "return_pct": float(t.return_pct),
            "duration_bars": int(t.duration_bars),
            "exit_reason": str(t.exit_reason)
        })

    monthly_returns: List[Dict[str, Any]] = []
    if not result.daily_returns.empty:
        dr = result.daily_returns.to_frame(name='ret')
        if isinstance(dr.index, pd.DatetimeIndex):
            monthly_rets = dr.resample('ME').apply(lambda x: (1 + x).prod() - 1)
            for date, row in monthly_rets.iterrows():
                monthly_returns.append({
                    "year": int(date.year), # type: ignore
                    "month": int(date.month), # type: ignore
                    "return_pct": float(row['ret']) if pd.notna(row['ret']) else 0.0
                })

    return {
        "metadata": {
            "ticker": ticker,
            "strategy_name": strategy_name
        },
        "metrics": result.metrics,
        "equity_curve": equity_curve_data,
        "trades": trades_data,
        "monthly_returns": monthly_returns
    }

import pandas as pd
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any
import logging
from ..risk.metrics import calculate_all_risk_metrics, calculate_max_drawdown

logger = logging.getLogger(__name__)

class Trade(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    size: float
    side: str
    pnl: float
    return_pct: float
    duration_bars: int
    exit_reason: str

class BacktestResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    equity_curve: pd.Series
    drawdown_series: pd.Series
    trades: List[Trade]
    daily_returns: pd.Series
    benchmark_equity: pd.Series
    metrics: Dict[str, Any]

class BacktestEngine:
    def __init__(self):
        pass

    def run(
        self, 
        df: pd.DataFrame, 
        signals: pd.Series, 
        initial_capital: float = 10000.0, 
        commission_pct: float = 0.001, 
        slippage_pct: float = 0.0005, 
        allow_short: bool = False
    ) -> BacktestResult:
        if df.empty or signals.empty:
            raise ValueError("Dataframe or signals cannot be empty")
            
        close_prices = df['close'] if 'close' in df.columns else df.iloc[:, 0]
        dates = df.index
        
        equity = [initial_capital] * len(df)
        trades: List[Trade] = []
        
        position = 0
        entry_price = 0.0
        entry_time = None
        entry_idx = 0
        cash = initial_capital
        units = 0.0
        
        for i in range(len(df)):
            price = float(close_prices.iloc[i])
            signal = int(signals.iloc[i])
            date = dates[i]
            
            if not allow_short and signal == -1:
                signal = 0
                
            if signal != position and signal != 0:
                if position != 0:
                    exit_price = price * (1 - slippage_pct) if position == 1 else price * (1 + slippage_pct)
                    commission = abs(units * exit_price * commission_pct)
                    pnl = (exit_price - entry_price) * units if position == 1 else (entry_price - exit_price) * units
                    pnl -= commission
                    cash += (units * exit_price) if position == 1 else (-units * exit_price)
                    cash -= commission
                    
                    ret_pct = pnl / (abs(units) * entry_price) if entry_price > 0 else 0.0
                    
                    trades.append(Trade(
                        entry_time=entry_time, # type: ignore
                        exit_time=date,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        size=abs(units),
                        side="long" if position == 1 else "short",
                        pnl=pnl,
                        return_pct=ret_pct,
                        duration_bars=i - entry_idx,
                        exit_reason="signal_reversal"
                    ))
                    units = 0.0
                
                position = signal
                entry_time = date
                entry_idx = i
                entry_price = price * (1 + slippage_pct) if position == 1 else price * (1 - slippage_pct)
                
                trade_value = cash * 0.99
                units = trade_value / entry_price
                commission = trade_value * commission_pct
                cash -= (trade_value + commission) if position == 1 else (-trade_value + commission)

            elif signal == 0 and position != 0:
                exit_price = price * (1 - slippage_pct) if position == 1 else price * (1 + slippage_pct)
                commission = abs(units * exit_price * commission_pct)
                pnl = (exit_price - entry_price) * units if position == 1 else (entry_price - exit_price) * units
                pnl -= commission
                cash += (units * exit_price) if position == 1 else (-units * exit_price)
                cash -= commission
                
                ret_pct = pnl / (abs(units) * entry_price) if entry_price > 0 else 0.0
                
                trades.append(Trade(
                    entry_time=entry_time, # type: ignore
                    exit_time=date,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    size=abs(units),
                    side="long" if position == 1 else "short",
                    pnl=pnl,
                    return_pct=ret_pct,
                    duration_bars=i - entry_idx,
                    exit_reason="exit_signal"
                ))
                position = 0
                units = 0.0

            current_value = cash
            if position == 1:
                current_value += units * price
            elif position == -1:
                current_value -= units * price 
                
            equity[i] = current_value

        equity_curve = pd.Series(equity, index=dates)
        daily_returns = equity_curve.pct_change().fillna(0.0)
        
        benchmark_returns = close_prices.pct_change().fillna(0.0)
        benchmark_equity = initial_capital * (1 + benchmark_returns).cumprod()

        trade_returns = [t.return_pct for t in trades]
        
        metrics = calculate_all_risk_metrics(
            returns=daily_returns,
            equity_curve=equity_curve,
            trade_returns=trade_returns,
            benchmark_returns=benchmark_returns
        )
        
        _, drawdown_series = calculate_max_drawdown(equity_curve)

        return BacktestResult(
            equity_curve=equity_curve,
            drawdown_series=drawdown_series,
            trades=trades,
            daily_returns=daily_returns,
            benchmark_equity=benchmark_equity,
            metrics=metrics
        )

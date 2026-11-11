import pandas as pd
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

STRATEGY_CATALOG: Dict[str, Any] = {
    "SMA_CROSSOVER": {
        "description": "Simple Moving Average Crossover",
        "params": {
            "fast_period": {"type": "int", "default": 20, "min": 2, "max": 200},
            "slow_period": {"type": "int", "default": 50, "min": 5, "max": 500}
        }
    },
    "RSI_MOMENTUM": {
        "description": "Relative Strength Index Momentum",
        "params": {
            "period": {"type": "int", "default": 14, "min": 2, "max": 100},
            "oversold": {"type": "int", "default": 30, "min": 0, "max": 50},
            "overbought": {"type": "int", "default": 70, "min": 50, "max": 100}
        }
    },
    "MACD_CROSSOVER": {
        "description": "Moving Average Convergence Divergence Crossover",
        "params": {
            "fast": {"type": "int", "default": 12, "min": 2, "max": 100},
            "slow": {"type": "int", "default": 26, "min": 5, "max": 200},
            "signal": {"type": "int", "default": 9, "min": 2, "max": 50}
        }
    },
    "SENTIMENT_ENHANCED": {
        "description": "Sentiment Enhanced Strategy",
        "params": {
            "fast_period": {"type": "int", "default": 20, "min": 2, "max": 200},
            "slow_period": {"type": "int", "default": 50, "min": 5, "max": 500},
            "sentiment_threshold": {"type": "float", "default": 0.15, "min": -1.0, "max": 1.0}
        }
    },
    "BOLLINGER_BREAKOUT": {
        "description": "Bollinger Bands Breakout",
        "params": {
            "period": {"type": "int", "default": 20, "min": 2, "max": 200},
            "std_dev": {"type": "float", "default": 2.0, "min": 0.5, "max": 5.0}
        }
    }
}

def generate_signals(df: pd.DataFrame, strategy_name: str, params: Optional[Dict[str, Any]] = None) -> pd.Series:
    """Generates target positions (-1, 0, 1) shifted by 1 to avoid lookahead bias."""
    if df.empty:
        return pd.Series(dtype=int)
        
    p = {}
    if strategy_name in STRATEGY_CATALOG:
        for k, v in STRATEGY_CATALOG[strategy_name]["params"].items():
            p[k] = v["default"]
    if params:
        p.update(params)

    signals = pd.Series(0, index=df.index)
    close = df['close'] if 'close' in df.columns else df.iloc[:, 0]

    try:
        if strategy_name == "SMA_CROSSOVER":
            fast_ma = close.rolling(window=int(p['fast_period'])).mean()
            slow_ma = close.rolling(window=int(p['slow_period'])).mean()
            signals[fast_ma > slow_ma] = 1
            signals[fast_ma < slow_ma] = -1

        elif strategy_name == "RSI_MOMENTUM":
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=int(p['period'])).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=int(p['period'])).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            signals[rsi < p['oversold']] = 1
            signals[rsi > p['overbought']] = -1

        elif strategy_name == "MACD_CROSSOVER":
            ema_fast = close.ewm(span=int(p['fast']), adjust=False).mean()
            ema_slow = close.ewm(span=int(p['slow']), adjust=False).mean()
            macd = ema_fast - ema_slow
            signal_line = macd.ewm(span=int(p['signal']), adjust=False).mean()
            
            signals[macd > signal_line] = 1
            signals[macd < signal_line] = -1

        elif strategy_name == "SENTIMENT_ENHANCED":
            fast_ma = close.rolling(window=int(p['fast_period'])).mean()
            slow_ma = close.rolling(window=int(p['slow_period'])).mean()
            
            if 'compound_score' in df.columns:
                sent_ok = df['compound_score'] > p['sentiment_threshold']
                signals[(fast_ma > slow_ma) & sent_ok] = 1
                signals[fast_ma < slow_ma] = -1
            else:
                signals[fast_ma > slow_ma] = 1
                signals[fast_ma < slow_ma] = -1

        elif strategy_name == "BOLLINGER_BREAKOUT":
            sma = close.rolling(window=int(p['period'])).mean()
            std = close.rolling(window=int(p['period'])).std()
            upper = sma + (std * p['std_dev'])
            lower = sma - (std * p['std_dev'])
            
            signals[close > upper] = 1
            signals[close < lower] = -1
            
    except Exception as e:
        logger.error(f"Error generating signals for {strategy_name}: {e}")

    # CRITICAL: Shift by 1 to eliminate lookahead bias
    return signals.shift(1).fillna(0).astype(int)

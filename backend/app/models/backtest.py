from pydantic import BaseModel, ConfigDict, Field
from typing import Any, List, Dict
from .risk import RiskMetrics

class BacktestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    ticker: str
    strategy: str
    params: dict[str, Any] = Field(default_factory=dict)
    period: str = "1y"
    interval: str = "1d"
    initial_capital: float = 10000.0
    commission_pct: float = 0.001
    slippage_pct: float = 0.0005
    include_sentiment: bool = False

class EquityPoint(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    timestamp: str
    equity: float
    benchmark: float
    drawdown: float

class TradeRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    side: str
    pnl: float
    return_pct: float
    duration_bars: int

class StrategyParamInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    name: str
    type: str
    default: Any
    description: str

class StrategyInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    name: str
    description: str
    parameters: List[StrategyParamInfo]

class BacktestDataPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    ticker: str
    strategy: str
    metrics: RiskMetrics
    equity_curve: List[EquityPoint]
    trades: List[TradeRecord]
    monthly_returns: List[dict[str, Any]]

class BacktestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    status: str = "ok"
    data: BacktestDataPayload
    meta: dict[str, Any]

class StrategyListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    status: str = "ok"
    data: List[StrategyInfo]

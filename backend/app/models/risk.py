from pydantic import BaseModel, ConfigDict
from typing import Any, List

class RiskMetrics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    total_roi: float
    annualized_roi: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_trade_return: float
    volatility_annualized: float

class RiskEvaluationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    returns: List[float]
    risk_free_rate: float = 0.02

class RiskEvaluationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    
    status: str = "ok"
    data: RiskMetrics
    meta: dict[str, Any]

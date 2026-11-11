import logging
import numpy as np
from fastapi import APIRouter, HTTPException
from ...models.risk import RiskEvaluationRequest, RiskEvaluationResponse, RiskMetrics

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/evaluate", response_model=RiskEvaluationResponse)
async def evaluate_risk(request: RiskEvaluationRequest):
    """
    Evaluate risk metrics from a list of returns.
    """
    try:
        returns = np.array(request.returns)
        if len(returns) == 0:
            raise ValueError("Returns list cannot be empty")
            
        total_roi = float(np.prod(1 + returns) - 1)
        annualized_roi = float((1 + total_roi) ** (252 / max(len(returns), 1)) - 1)
        
        std_dev = float(np.std(returns)) if len(returns) > 1 else 0.0
        volatility_annualized = std_dev * np.sqrt(252)
        
        sharpe_ratio = float((annualized_roi - request.risk_free_rate) / volatility_annualized) if volatility_annualized > 0 else 0.0
        
        downside_returns = returns[returns < 0]
        downside_std = float(np.std(downside_returns)) if len(downside_returns) > 1 else 0.0
        downside_vol = downside_std * np.sqrt(252)
        sortino_ratio = float((annualized_roi - request.risk_free_rate) / downside_vol) if downside_vol > 0 else 0.0
        
        cum_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cum_returns)
        drawdowns = (cum_returns - running_max) / running_max
        max_drawdown = float(abs(np.min(drawdowns))) if len(drawdowns) > 0 else 0.0
        
        calmar_ratio = float(annualized_roi / max_drawdown) if max_drawdown > 0 else 0.0
        
        winning_trades = int(np.sum(returns > 0))
        losing_trades = int(np.sum(returns < 0))
        total_trades = winning_trades + losing_trades
        
        win_rate = float(winning_trades / total_trades) if total_trades > 0 else 0.0
        
        gross_profit = float(np.sum(returns[returns > 0]))
        gross_loss = float(abs(np.sum(returns[returns < 0])))
        profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else float(gross_profit)
        
        avg_trade_return = float(np.mean(returns)) if len(returns) > 0 else 0.0
        
        metrics = RiskMetrics(
            total_roi=total_roi,
            annualized_roi=annualized_roi,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_trade_return=avg_trade_return,
            volatility_annualized=volatility_annualized
        )
        
        return RiskEvaluationResponse(status="ok", data=metrics, meta={"count": len(returns)})
    except Exception as e:
        logger.error(f"Risk evaluation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

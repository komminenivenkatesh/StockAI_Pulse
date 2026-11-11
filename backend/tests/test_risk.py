import pytest
import numpy as np
from app.models.risk import RiskEvaluationRequest
from app.api.v1.risk import evaluate_risk

@pytest.mark.asyncio
async def test_evaluate_risk_standard():
    returns = [0.01, 0.02, -0.01, 0.03, -0.02, 0.01]
    request = RiskEvaluationRequest(returns=returns, risk_free_rate=0.0)
    response = await evaluate_risk(request)
    
    assert response.status == "ok"
    assert response.data.total_trades == 6
    assert response.data.winning_trades == 4
    assert response.data.losing_trades == 2
    assert response.data.win_rate == 4/6
    assert response.data.profit_factor > 0
    assert response.data.max_drawdown > 0

@pytest.mark.asyncio
async def test_evaluate_risk_empty():
    request = RiskEvaluationRequest(returns=[], risk_free_rate=0.0)
    with pytest.raises(Exception):
        await evaluate_risk(request)

@pytest.mark.asyncio
async def test_evaluate_risk_all_gains():
    returns = [0.01, 0.02, 0.01]
    request = RiskEvaluationRequest(returns=returns, risk_free_rate=0.0)
    response = await evaluate_risk(request)
    
    assert response.data.losing_trades == 0
    assert response.data.win_rate == 1.0
    assert response.data.max_drawdown == 0.0

@pytest.mark.asyncio
async def test_evaluate_risk_all_losses():
    returns = [-0.01, -0.02, -0.01]
    request = RiskEvaluationRequest(returns=returns, risk_free_rate=0.0)
    response = await evaluate_risk(request)
    
    assert response.data.winning_trades == 0
    assert response.data.win_rate == 0.0
    assert response.data.profit_factor == 0.0

@pytest.mark.asyncio
async def test_evaluate_risk_zero_variance():
    returns = [0.01, 0.01, 0.01, 0.01]
    request = RiskEvaluationRequest(returns=returns, risk_free_rate=0.0)
    response = await evaluate_risk(request)
    
    assert response.data.volatility_annualized == 0.0
    assert response.data.sharpe_ratio == 0.0

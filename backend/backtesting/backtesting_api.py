from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from .backtesting_engine import BacktestingEngine, TrendFollowingStrategy

router = APIRouter()

class BacktestRequest(BaseModel):
    strategy: str  # 'trend' ou autre
    historical_data: list
    initial_balance: float = 1000
    market_cap_filter: str = 'all'  # 'all', 'low', 'high'

@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    # Log du filtre market cap choisi
    print(f"[Backtest] Filtre market cap: {request.market_cap_filter}")
    # Select strategy
    if request.strategy == 'trend':
        strategy = TrendFollowingStrategy(initial_balance=request.initial_balance)
    else:
        raise HTTPException(status_code=400, detail="Unknown strategy. Utilisez 'trend'.")
    # (Optionnel) Ici, on pourrait filtrer côté backend aussi selon request.market_cap_filter
    engine = BacktestingEngine(strategy, request.historical_data)
    results = engine.run()
    performance = engine.get_performance()
    return {"results": results, "performance": performance}

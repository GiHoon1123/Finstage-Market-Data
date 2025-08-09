from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class TrackingSummaryResponse(BaseModel):
    total_tracked: int
    completed: int
    pending: int
    completion_rate: float


class SignalPerformanceResponse(BaseModel):
    signal_type: str
    total_signals: int
    avg_return_1h: Optional[float]
    avg_return_1d: Optional[float]
    avg_return_1w: Optional[float]
    success_rate_1h: float
    success_rate_1d: float
    success_rate_1w: float


class BacktestingResultResponse(BaseModel):
    strategy_name: str
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int


class PendingOutcomeResponse(BaseModel):
    outcome_id: int
    signal_id: int
    signal_type: str
    symbol: str
    signal_time: datetime
    elapsed_hours: float
    price_1h_completed: bool
    price_1d_completed: bool

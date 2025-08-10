from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TrackingSummaryResponse(BaseModel):
    """결과 추적 현황 요약 응답"""

    total_tracked: int = Field(
        ..., example=150, description="총 추적 중인 신호 수", ge=0
    )
    completed: int = Field(..., example=120, description="완료된 추적 수", ge=0)
    pending: int = Field(..., example=30, description="진행 중인 추적 수", ge=0)
    completion_rate: float = Field(
        ..., example=80.0, description="완료율 (%)", ge=0.0, le=100.0
    )

    class Config:
        schema_extra = {
            "example": {
                "total_tracked": 150,
                "completed": 120,
                "pending": 30,
                "completion_rate": 80.0,
            }
        }


class SignalPerformanceResponse(BaseModel):
    """신호 성과 분석 응답"""

    signal_type: str = Field(
        ..., example="BUY", description="신호 타입 (BUY, SELL, HOLD)"
    )
    total_signals: int = Field(..., example=45, description="총 신호 수", ge=0)
    avg_return_1h: Optional[float] = Field(
        None, example=0.25, description="1시간 평균 수익률 (%)"
    )
    avg_return_1d: Optional[float] = Field(
        None, example=1.15, description="1일 평균 수익률 (%)"
    )
    avg_return_1w: Optional[float] = Field(
        None, example=3.45, description="1주 평균 수익률 (%)"
    )
    success_rate_1h: float = Field(
        ..., example=65.5, description="1시간 성공률 (%)", ge=0.0, le=100.0
    )
    success_rate_1d: float = Field(
        ..., example=72.3, description="1일 성공률 (%)", ge=0.0, le=100.0
    )
    success_rate_1w: float = Field(
        ..., example=68.9, description="1주 성공률 (%)", ge=0.0, le=100.0
    )

    class Config:
        schema_extra = {
            "example": {
                "signal_type": "BUY",
                "total_signals": 45,
                "avg_return_1h": 0.25,
                "avg_return_1d": 1.15,
                "avg_return_1w": 3.45,
                "success_rate_1h": 65.5,
                "success_rate_1d": 72.3,
                "success_rate_1w": 68.9,
            }
        }


class BacktestingResultResponse(BaseModel):
    """백테스팅 결과 응답"""

    strategy_name: str = Field(
        ..., example="RSI Oversold Strategy", description="전략명"
    )
    total_return: float = Field(..., example=15.67, description="총 수익률 (%)")
    annual_return: float = Field(..., example=12.34, description="연간 수익률 (%)")
    max_drawdown: float = Field(..., example=-8.45, description="최대 손실률 (%)")
    sharpe_ratio: float = Field(..., example=1.23, description="샤프 비율")
    win_rate: float = Field(..., example=68.5, description="승률 (%)", ge=0.0, le=100.0)
    total_trades: int = Field(..., example=156, description="총 거래 수", ge=0)

    class Config:
        schema_extra = {
            "example": {
                "strategy_name": "RSI Oversold Strategy",
                "total_return": 15.67,
                "annual_return": 12.34,
                "max_drawdown": -8.45,
                "sharpe_ratio": 1.23,
                "win_rate": 68.5,
                "total_trades": 156,
            }
        }


class PendingOutcomeResponse(BaseModel):
    """대기 중인 결과 응답"""

    outcome_id: int = Field(..., example=12345, description="결과 추적 ID")
    signal_id: int = Field(..., example=67890, description="신호 ID")
    signal_type: str = Field(..., example="BUY", description="신호 타입")
    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    signal_time: datetime = Field(
        ..., example="2025-08-09T10:30:00Z", description="신호 발생 시간"
    )
    elapsed_hours: float = Field(
        ..., example=2.5, description="경과 시간 (시간)", ge=0.0
    )
    price_1h_completed: bool = Field(
        ..., example=True, description="1시간 가격 추적 완료 여부"
    )
    price_1d_completed: bool = Field(
        ..., example=False, description="1일 가격 추적 완료 여부"
    )

    class Config:
        schema_extra = {
            "example": {
                "outcome_id": 12345,
                "signal_id": 67890,
                "signal_type": "BUY",
                "symbol": "AAPL",
                "signal_time": "2025-08-09T10:30:00Z",
                "elapsed_hours": 2.5,
                "price_1h_completed": True,
                "price_1d_completed": False,
            }
        }

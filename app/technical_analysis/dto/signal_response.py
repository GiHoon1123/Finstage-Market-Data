from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class TechnicalSignalResponse(BaseModel):
    """기술적 신호 응답 모델"""

    id: int = Field(..., example=12345, description="신호 ID")
    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    signal_type: str = Field(..., example="MA200_breakout_up", description="신호 타입")
    timeframe: str = Field(..., example="1d", description="시간대")
    signal_time: datetime = Field(
        ..., example="2025-08-09T10:30:00Z", description="신호 발생 시간"
    )
    price: Optional[float] = Field(
        None, example=150.25, description="신호 발생 시점 가격"
    )
    strength: Optional[float] = Field(
        None, example=0.85, description="신호 강도 (0.0 ~ 1.0)", ge=0.0, le=1.0
    )
    confidence: Optional[float] = Field(
        None, example=0.75, description="신뢰도 (0.0 ~ 1.0)", ge=0.0, le=1.0
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="추가 메타데이터")

    class Config:
        schema_extra = {
            "example": {
                "id": 12345,
                "symbol": "AAPL",
                "signal_type": "MA200_breakout_up",
                "timeframe": "1d",
                "signal_time": "2025-08-09T10:30:00Z",
                "price": 150.25,
                "strength": 0.85,
                "confidence": 0.75,
                "metadata": {"ma200_value": 148.50, "volume": 1000000},
            }
        }


class SignalListResponse(BaseModel):
    """신호 목록 응답 모델"""

    total_count: int = Field(..., example=25, description="총 신호 수", ge=0)
    filtered_count: int = Field(..., example=15, description="필터링된 신호 수", ge=0)
    signals: List[TechnicalSignalResponse] = Field(..., description="신호 목록")
    filters: Dict[str, Any] = Field(..., description="적용된 필터 조건")
    query_time: str = Field(
        ..., example="2025-08-09T12:00:00Z", description="조회 시간"
    )

    class Config:
        schema_extra = {
            "example": {
                "total_count": 25,
                "filtered_count": 15,
                "signals": [
                    {
                        "id": 12345,
                        "symbol": "AAPL",
                        "signal_type": "MA200_breakout_up",
                        "timeframe": "1d",
                        "signal_time": "2025-08-09T10:30:00Z",
                        "price": 150.25,
                        "strength": 0.85,
                        "confidence": 0.75,
                    }
                ],
                "filters": {"symbol": "AAPL", "hours": 24, "limit": 50},
                "query_time": "2025-08-09T12:00:00Z",
            }
        }

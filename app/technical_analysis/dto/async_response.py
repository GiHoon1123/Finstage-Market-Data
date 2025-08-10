from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


class AsyncPriceResponse(BaseModel):
    """비동기 가격 조회 응답 모델"""

    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    current_price: Optional[float] = Field(
        None, example=150.25, description="현재 가격"
    )
    price_change: Optional[float] = Field(None, example=2.15, description="가격 변동")
    price_change_percent: Optional[float] = Field(
        None, example=1.45, description="가격 변동률 (%)"
    )
    volume: Optional[int] = Field(None, example=1000000, description="거래량")
    market_cap: Optional[float] = Field(
        None, example=2500000000000, description="시가총액"
    )
    timestamp: str = Field(..., example="2025-08-09T12:00:00Z", description="조회 시간")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "current_price": 150.25,
                "price_change": 2.15,
                "price_change_percent": 1.45,
                "volume": 1000000,
                "market_cap": 2500000000000,
                "timestamp": "2025-08-09T12:00:00Z",
            }
        }

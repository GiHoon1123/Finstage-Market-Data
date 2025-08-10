from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime


class CurrentPriceResponse(BaseModel):
    """현재 가격 응답 모델"""

    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    current_price: float = Field(..., example=150.25, description="현재 가격 (달러)")
    timestamp: str = Field(..., example="2025-08-09T12:00:00", description="조회 시간")
    details: Optional[Dict[str, Any]] = Field(
        None, description="상세 정보 (include_details=true일 때)"
    )

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "current_price": 150.25,
                "timestamp": "2025-08-09T12:00:00",
                "details": {
                    "price_summary": {"high": 152.0, "low": 148.5},
                    "snapshot_summary": {"volume": 1000000},
                    "high_record_summary": {"all_time_high": 180.0},
                },
            }
        }


class BatchPriceResponse(BaseModel):
    """배치 가격 조회 응답 모델"""

    total_symbols: int = Field(..., example=5, description="총 조회 심볼 수", ge=0)
    successful_count: int = Field(..., example=4, description="성공한 조회 수", ge=0)
    results: Dict[str, Optional[float]] = Field(..., description="심볼별 가격 결과")
    timestamp: str = Field(..., example="2025-08-09T12:00:00", description="조회 시간")

    class Config:
        schema_extra = {
            "example": {
                "total_symbols": 3,
                "successful_count": 2,
                "results": {"AAPL": 150.25, "MSFT": 280.50, "GOOGL": None},
                "timestamp": "2025-08-09T12:00:00",
            }
        }


class PriceHistoryResponse(BaseModel):
    """가격 히스토리 응답 모델"""

    symbol: str = Field(..., example="AAPL", description="주식 심볼")
    period: str = Field(..., example="1mo", description="조회 기간")
    interval: str = Field(..., example="1d", description="데이터 간격")
    data_points: int = Field(..., example=30, description="데이터 포인트 수", ge=0)
    history: Dict[str, Any] = Field(..., description="히스토리 데이터")
    timestamp: str = Field(..., example="2025-08-09T12:00:00", description="조회 시간")

    class Config:
        schema_extra = {
            "example": {
                "symbol": "AAPL",
                "period": "1mo",
                "interval": "1d",
                "data_points": 30,
                "history": {
                    "timestamps": ["2025-07-10", "2025-07-11"],
                    "prices": [148.5, 150.25],
                },
                "timestamp": "2025-08-09T12:00:00",
            }
        }


class BackgroundTaskResponse(BaseModel):
    """백그라운드 작업 응답 모델"""

    status: str = Field(..., example="queued", description="작업 상태")
    task_id: str = Field(..., example="task_12345", description="작업 ID")
    symbols: List[str] = Field(..., description="처리할 심볼 목록")
    period: str = Field(..., example="1y", description="수집 기간")
    estimated_completion: str = Field(
        ..., example="10-30 minutes", description="예상 완료 시간"
    )
    queued_at: str = Field(
        ..., example="2025-08-09T12:00:00", description="큐 등록 시간"
    )

    class Config:
        schema_extra = {
            "example": {
                "status": "queued",
                "task_id": "task_12345",
                "symbols": ["AAPL", "MSFT", "GOOGL"],
                "period": "1y",
                "estimated_completion": "10-30 minutes",
                "queued_at": "2025-08-09T12:00:00",
            }
        }

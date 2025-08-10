from pydantic import BaseModel, Field
from typing import Dict, Any, List


class ServiceHealthResponse(BaseModel):
    """서비스 상태 응답 모델"""

    service_name: str = Field(
        ..., example="Technical Analysis Service", description="서비스명"
    )
    status: str = Field(..., example="healthy", description="서비스 상태")
    version: str = Field(..., example="1.2.0", description="서비스 버전")
    uptime: str = Field(..., example="5d 12h 30m", description="가동 시간")
    dependencies: Dict[str, str] = Field(..., description="의존성 서비스 상태")
    metrics: Dict[str, Any] = Field(..., description="성능 지표")

    class Config:
        schema_extra = {
            "example": {
                "service_name": "Technical Analysis Service",
                "status": "healthy",
                "version": "1.2.0",
                "uptime": "5d 12h 30m",
                "dependencies": {
                    "database": "connected",
                    "redis": "connected",
                    "yahoo_finance": "available",
                },
                "metrics": {
                    "requests_per_minute": 45,
                    "avg_response_time": "120ms",
                    "error_rate": 0.02,
                },
            }
        }


class SignalTypesResponse(BaseModel):
    """지원하는 신호 타입 응답 모델"""

    total_types: int = Field(..., example=15, description="총 신호 타입 수", ge=0)
    categories: Dict[str, List[str]] = Field(..., description="카테고리별 신호 타입")
    descriptions: Dict[str, str] = Field(..., description="신호 타입별 설명")

    class Config:
        schema_extra = {
            "example": {
                "total_types": 15,
                "categories": {
                    "moving_average": ["MA50_crossover", "MA200_breakout"],
                    "momentum": ["RSI_oversold", "RSI_overbought"],
                    "trend": ["MACD_bullish", "MACD_bearish"],
                },
                "descriptions": {
                    "MA50_crossover": "50일 이동평균선 교차",
                    "RSI_oversold": "RSI 과매도 신호",
                },
            }
        }

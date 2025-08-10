from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class TestAlertResponse(BaseModel):
    """알림 테스트 응답 모델"""

    success: bool = Field(..., example=True, description="테스트 성공 여부")
    message: str = Field(
        ...,
        example="이동평균선 돌파 알림 테스트가 성공적으로 실행되었습니다.",
        description="테스트 결과 메시지",
    )
    symbol: Optional[str] = Field(None, example="AAPL", description="테스트한 심볼")
    alert_type: Optional[str] = Field(
        None, example="MA_BREAKOUT", description="알림 타입"
    )
    test_data: Optional[Dict[str, Any]] = Field(
        None, description="테스트 데이터 상세 정보"
    )
    timestamp: str = Field(
        ..., example="2025-08-09T12:00:00Z", description="테스트 실행 시간"
    )

    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "message": "이동평균선 돌파 알림 테스트 완료",
                "symbol": "AAPL",
                "alert_type": "MA_BREAKOUT",
                "test_data": {
                    "current_price": 150.25,
                    "ma200": 148.50,
                    "breakout_strength": 0.85,
                },
                "timestamp": "2025-08-09T12:00:00Z",
            }
        }


class EnvironmentCheckResponse(BaseModel):
    """환경 변수 확인 응답 모델"""

    telegram_configured: bool = Field(
        ..., example=True, description="텔레그램 설정 여부"
    )
    database_connected: bool = Field(
        ..., example=True, description="데이터베이스 연결 상태"
    )
    api_keys_valid: bool = Field(..., example=True, description="API 키 유효성")
    environment: str = Field(..., example="development", description="실행 환경")
    config_details: Dict[str, Any] = Field(..., description="설정 상세 정보")
    timestamp: str = Field(..., example="2025-08-09T12:00:00Z", description="확인 시간")

    class Config:
        schema_extra = {
            "example": {
                "telegram_configured": True,
                "database_connected": True,
                "api_keys_valid": True,
                "environment": "development",
                "config_details": {
                    "telegram_bot_token": "configured",
                    "database_url": "connected",
                    "yahoo_finance_api": "available",
                },
                "timestamp": "2025-08-09T12:00:00Z",
            }
        }

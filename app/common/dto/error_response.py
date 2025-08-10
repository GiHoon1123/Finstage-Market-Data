from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorResponse(BaseModel):
    """공통 에러 응답 모델"""

    error: str = Field(..., example="VALIDATION_ERROR", description="에러 코드")
    message: str = Field(..., example="잘못된 입력값입니다", description="에러 메시지")
    details: Optional[Dict[str, Any]] = Field(
        None,
        example={"field": "symbol", "value": "invalid"},
        description="상세 에러 정보",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        example="2025-08-09T12:00:00Z",
        description="에러 발생 시간",
    )

    class Config:
        schema_extra = {
            "example": {
                "error": "VALIDATION_ERROR",
                "message": "잘못된 입력값입니다",
                "details": {"field": "symbol", "value": "invalid"},
                "timestamp": "2025-08-09T12:00:00Z",
            }
        }


class ValidationErrorResponse(ErrorResponse):
    """검증 에러 응답 모델"""

    error: str = Field(default="VALIDATION_ERROR", description="검증 에러 코드")


class NotFoundErrorResponse(ErrorResponse):
    """리소스 없음 에러 응답 모델"""

    error: str = Field(default="NOT_FOUND", description="리소스 없음 에러 코드")


class ServerErrorResponse(ErrorResponse):
    """서버 에러 응답 모델"""

    error: str = Field(default="INTERNAL_SERVER_ERROR", description="서버 에러 코드")

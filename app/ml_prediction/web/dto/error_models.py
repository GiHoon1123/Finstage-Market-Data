"""
ML 예측 API 에러 모델

이 파일은 ML 예측 API의 에러 응답 모델들을 정의합니다.
다양한 에러 상황에 대한 구조화된 응답을 제공합니다.

주요 에러 타입:
- 검증 에러
- 모델 관련 에러
- 데이터 관련 에러
- 시스템 에러
"""

from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class ErrorCode(str, Enum):
    """에러 코드"""

    # 일반 에러
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # 모델 관련 에러
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    MODEL_TRAINING_FAILED = "MODEL_TRAINING_FAILED"
    MODEL_PREDICTION_FAILED = "MODEL_PREDICTION_FAILED"
    MODEL_EVALUATION_FAILED = "MODEL_EVALUATION_FAILED"
    MODEL_ALREADY_EXISTS = "MODEL_ALREADY_EXISTS"
    NO_ACTIVE_MODEL = "NO_ACTIVE_MODEL"
    MODEL_LOADING_FAILED = "MODEL_LOADING_FAILED"

    # 데이터 관련 에러
    DATA_NOT_FOUND = "DATA_NOT_FOUND"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DATA_QUALITY_ERROR = "DATA_QUALITY_ERROR"
    DATA_SOURCE_UNAVAILABLE = "DATA_SOURCE_UNAVAILABLE"

    # 예측 관련 에러
    PREDICTION_FAILED = "PREDICTION_FAILED"
    PREDICTION_NOT_FOUND = "PREDICTION_NOT_FOUND"
    INVALID_TIMEFRAME = "INVALID_TIMEFRAME"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"

    # 백테스트 관련 에러
    BACKTEST_FAILED = "BACKTEST_FAILED"
    INVALID_BACKTEST_CONFIG = "INVALID_BACKTEST_CONFIG"

    # 권한 관련 에러
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"

    # 리소스 관련 에러
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


class ValidationErrorDetail(BaseModel):
    """검증 에러 상세"""

    field: str = Field(..., description="에러가 발생한 필드")

    message: str = Field(..., description="에러 메시지")

    invalid_value: Optional[Any] = Field(default=None, description="잘못된 값")

    constraint: Optional[str] = Field(default=None, description="위반된 제약 조건")


class ErrorResponse(BaseModel):
    """기본 에러 응답"""

    status: str = Field(default="failed", description="응답 상태")

    error_code: ErrorCode = Field(..., description="에러 코드")

    message: str = Field(..., description="에러 메시지")

    details: Optional[Dict[str, Any]] = Field(
        default=None, description="에러 상세 정보"
    )

    timestamp: str = Field(..., description="에러 발생 시간 (ISO 형식)")

    request_id: Optional[str] = Field(default=None, description="요청 ID (추적용)")


class ValidationErrorResponse(ErrorResponse):
    """검증 에러 응답"""

    error_code: ErrorCode = Field(
        default=ErrorCode.VALIDATION_ERROR, description="에러 코드"
    )

    validation_errors: List[ValidationErrorDetail] = Field(
        ..., description="검증 에러 목록"
    )


class ModelErrorResponse(ErrorResponse):
    """모델 관련 에러 응답"""

    model_name: Optional[str] = Field(default=None, description="관련 모델 이름")

    model_version: Optional[str] = Field(default=None, description="관련 모델 버전")

    symbol: Optional[str] = Field(default=None, description="관련 심볼")


class DataErrorResponse(ErrorResponse):
    """데이터 관련 에러 응답"""

    symbol: Optional[str] = Field(default=None, description="관련 심볼")

    date_range: Optional[Dict[str, str]] = Field(
        default=None, description="관련 날짜 범위"
    )

    data_source: Optional[str] = Field(default=None, description="관련 데이터 소스")

    available_data_count: Optional[int] = Field(
        default=None, description="사용 가능한 데이터 개수"
    )

    required_data_count: Optional[int] = Field(
        default=None, description="필요한 데이터 개수"
    )


class PredictionErrorResponse(ErrorResponse):
    """예측 관련 에러 응답"""

    symbol: str = Field(..., description="관련 심볼")

    prediction_date: Optional[str] = Field(default=None, description="예측 날짜")

    timeframes: Optional[List[str]] = Field(
        default=None, description="관련 타임프레임들"
    )

    model_version: Optional[str] = Field(default=None, description="사용된 모델 버전")


class BacktestErrorResponse(ErrorResponse):
    """백테스트 관련 에러 응답"""

    symbol: str = Field(..., description="관련 심볼")

    model_version: str = Field(..., description="모델 버전")

    date_range: Dict[str, str] = Field(..., description="백테스트 날짜 범위")

    strategy: Optional[str] = Field(default=None, description="거래 전략")


class ResourceErrorResponse(ErrorResponse):
    """리소스 관련 에러 응답"""

    resource_type: str = Field(..., description="리소스 타입 (memory, cpu, disk, etc.)")

    current_usage: Optional[float] = Field(default=None, description="현재 사용량")

    limit: Optional[float] = Field(default=None, description="제한값")

    suggested_action: Optional[str] = Field(default=None, description="권장 조치")


class TimeoutErrorResponse(ErrorResponse):
    """타임아웃 에러 응답"""

    error_code: ErrorCode = Field(
        default=ErrorCode.TIMEOUT_ERROR, description="에러 코드"
    )

    operation: str = Field(..., description="타임아웃된 작업")

    timeout_seconds: float = Field(..., description="타임아웃 시간 (초)")

    elapsed_seconds: Optional[float] = Field(default=None, description="경과 시간 (초)")


# 에러 코드별 기본 메시지 매핑
ERROR_MESSAGES = {
    ErrorCode.INTERNAL_SERVER_ERROR: "Internal server error occurred",
    ErrorCode.INVALID_REQUEST: "Invalid request format or parameters",
    ErrorCode.VALIDATION_ERROR: "Request validation failed",
    ErrorCode.MODEL_NOT_FOUND: "Requested model not found",
    ErrorCode.MODEL_TRAINING_FAILED: "Model training failed",
    ErrorCode.MODEL_PREDICTION_FAILED: "Model prediction failed",
    ErrorCode.MODEL_EVALUATION_FAILED: "Model evaluation failed",
    ErrorCode.MODEL_ALREADY_EXISTS: "Model already exists",
    ErrorCode.NO_ACTIVE_MODEL: "No active model found",
    ErrorCode.MODEL_LOADING_FAILED: "Failed to load model",
    ErrorCode.DATA_NOT_FOUND: "Required data not found",
    ErrorCode.INSUFFICIENT_DATA: "Insufficient data for operation",
    ErrorCode.DATA_QUALITY_ERROR: "Data quality issues detected",
    ErrorCode.DATA_SOURCE_UNAVAILABLE: "Data source is unavailable",
    ErrorCode.PREDICTION_FAILED: "Prediction operation failed",
    ErrorCode.PREDICTION_NOT_FOUND: "Prediction not found",
    ErrorCode.INVALID_TIMEFRAME: "Invalid timeframe specified",
    ErrorCode.INVALID_SYMBOL: "Invalid symbol specified",
    ErrorCode.INVALID_DATE_RANGE: "Invalid date range specified",
    ErrorCode.BACKTEST_FAILED: "Backtest operation failed",
    ErrorCode.INVALID_BACKTEST_CONFIG: "Invalid backtest configuration",
    ErrorCode.UNAUTHORIZED: "Authentication required",
    ErrorCode.FORBIDDEN: "Access forbidden",
    ErrorCode.RESOURCE_LIMIT_EXCEEDED: "Resource limit exceeded",
    ErrorCode.TIMEOUT_ERROR: "Operation timed out",
}


# HTTP 상태 코드 매핑
ERROR_HTTP_STATUS = {
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.INVALID_REQUEST: 400,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.MODEL_NOT_FOUND: 404,
    ErrorCode.MODEL_TRAINING_FAILED: 500,
    ErrorCode.MODEL_PREDICTION_FAILED: 500,
    ErrorCode.MODEL_EVALUATION_FAILED: 500,
    ErrorCode.MODEL_ALREADY_EXISTS: 409,
    ErrorCode.NO_ACTIVE_MODEL: 404,
    ErrorCode.MODEL_LOADING_FAILED: 500,
    ErrorCode.DATA_NOT_FOUND: 404,
    ErrorCode.INSUFFICIENT_DATA: 400,
    ErrorCode.DATA_QUALITY_ERROR: 400,
    ErrorCode.DATA_SOURCE_UNAVAILABLE: 503,
    ErrorCode.PREDICTION_FAILED: 500,
    ErrorCode.PREDICTION_NOT_FOUND: 404,
    ErrorCode.INVALID_TIMEFRAME: 400,
    ErrorCode.INVALID_SYMBOL: 400,
    ErrorCode.INVALID_DATE_RANGE: 400,
    ErrorCode.BACKTEST_FAILED: 500,
    ErrorCode.INVALID_BACKTEST_CONFIG: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.RESOURCE_LIMIT_EXCEEDED: 429,
    ErrorCode.TIMEOUT_ERROR: 408,
}


def create_error_response(
    error_code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponse:
    """
    에러 응답 생성 헬퍼 함수

    Args:
        error_code: 에러 코드
        message: 커스텀 메시지 (기본값: 코드별 기본 메시지)
        details: 에러 상세 정보
        request_id: 요청 ID

    Returns:
        에러 응답 객체
    """
    from datetime import datetime

    return ErrorResponse(
        error_code=error_code,
        message=message or ERROR_MESSAGES.get(error_code, "Unknown error"),
        details=details,
        timestamp=datetime.now().isoformat(),
        request_id=request_id,
    )


def create_validation_error_response(
    validation_errors: List[ValidationErrorDetail],
    message: Optional[str] = None,
    request_id: Optional[str] = None,
) -> ValidationErrorResponse:
    """
    검증 에러 응답 생성 헬퍼 함수

    Args:
        validation_errors: 검증 에러 목록
        message: 커스텀 메시지
        request_id: 요청 ID

    Returns:
        검증 에러 응답 객체
    """
    from datetime import datetime

    return ValidationErrorResponse(
        message=message or "Request validation failed",
        validation_errors=validation_errors,
        timestamp=datetime.now().isoformat(),
        request_id=request_id,
    )

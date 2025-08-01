"""
커스텀 예외 클래스 정의

애플리케이션 전체에서 사용할 표준화된 예외 클래스들
"""

from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(Enum):
    """에러 코드 정의"""

    # 일반적인 에러
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"

    # 데이터베이스 관련
    DATABASE_CONNECTION_ERROR = "DATABASE_CONNECTION_ERROR"
    DATABASE_QUERY_ERROR = "DATABASE_QUERY_ERROR"
    DATABASE_TRANSACTION_ERROR = "DATABASE_TRANSACTION_ERROR"

    # 외부 API 관련
    API_CONNECTION_ERROR = "API_CONNECTION_ERROR"
    API_TIMEOUT_ERROR = "API_TIMEOUT_ERROR"
    API_RATE_LIMIT_ERROR = "API_RATE_LIMIT_ERROR"
    API_AUTHENTICATION_ERROR = "API_AUTHENTICATION_ERROR"
    API_RESPONSE_ERROR = "API_RESPONSE_ERROR"

    # 데이터 처리 관련
    DATA_COLLECTION_ERROR = "DATA_COLLECTION_ERROR"
    DATA_PARSING_ERROR = "DATA_PARSING_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    DATA_NOT_FOUND_ERROR = "DATA_NOT_FOUND_ERROR"

    # 기술적 분석 관련
    ANALYSIS_CALCULATION_ERROR = "ANALYSIS_CALCULATION_ERROR"
    ANALYSIS_INSUFFICIENT_DATA_ERROR = "ANALYSIS_INSUFFICIENT_DATA_ERROR"
    ANALYSIS_INVALID_PARAMETER_ERROR = "ANALYSIS_INVALID_PARAMETER_ERROR"

    # 알림 관련
    NOTIFICATION_SEND_ERROR = "NOTIFICATION_SEND_ERROR"
    NOTIFICATION_FORMAT_ERROR = "NOTIFICATION_FORMAT_ERROR"

    # 스케줄러 관련
    SCHEDULER_ERROR = "SCHEDULER_ERROR"
    TASK_EXECUTION_ERROR = "TASK_EXECUTION_ERROR"


class FinstageException(Exception):
    """
    Finstage 애플리케이션 기본 예외 클래스

    모든 커스텀 예외의 베이스 클래스
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.original_exception = original_exception

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """예외 정보를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
            "original_error": (
                str(self.original_exception) if self.original_exception else None
            ),
        }

    def __str__(self) -> str:
        return f"[{self.error_code.value}] {self.message}"


class DatabaseError(FinstageException):
    """데이터베이스 관련 예외"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DATABASE_CONNECTION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message, error_code, details, original_exception)


class APIError(FinstageException):
    """외부 API 관련 예외"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.API_CONNECTION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message, error_code, details, original_exception)


class DataError(FinstageException):
    """데이터 처리 관련 예외"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.DATA_COLLECTION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message, error_code, details, original_exception)


class AnalysisError(FinstageException):
    """기술적 분석 관련 예외"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.ANALYSIS_CALCULATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message, error_code, details, original_exception)


class NotificationError(FinstageException):
    """알림 관련 예외"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.NOTIFICATION_SEND_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message, error_code, details, original_exception)


class SchedulerError(FinstageException):
    """스케줄러 관련 예외"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.SCHEDULER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message, error_code, details, original_exception)


class ValidationError(FinstageException):
    """검증 관련 예외"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        validation_details = details or {}
        if field:
            validation_details["field"] = field
        if value is not None:
            validation_details["value"] = str(value)

        super().__init__(
            message, ErrorCode.VALIDATION_ERROR, validation_details, original_exception
        )

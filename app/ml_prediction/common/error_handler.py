"""
ML 예측 통합 에러 핸들러

이 파일은 ML 예측 시스템의 통합 에러 처리 시스템을 구현합니다.
FastAPI 예외 핸들러와 로깅 시스템을 통합하여 일관된 에러 처리를 제공합니다.

주요 기능:
- 커스텀 예외 처리
- HTTP 예외 처리
- 검증 에러 처리
- 구조화된 에러 로깅
"""

from typing import Dict, Any, Optional, Union
from datetime import datetime
import traceback
import uuid
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError

from app.ml_prediction.common.exceptions import (
    MLPredictionError,
    ValidationError,
    EXCEPTION_MAPPING,
)
from app.ml_prediction.dto.error_models import (
    ErrorResponse,
    ValidationErrorResponse,
    ValidationErrorDetail,
    ErrorCode,
    create_error_response,
    create_validation_error_response,
    ERROR_HTTP_STATUS,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MLErrorHandler:
    """
    ML 예측 시스템 통합 에러 핸들러

    모든 ML 관련 에러를 일관되게 처리하고 로깅합니다.
    """

    def __init__(self):
        """에러 핸들러 초기화"""
        self.error_stats = {
            "total_errors": 0,
            "error_by_type": {},
            "error_by_endpoint": {},
            "last_reset": datetime.now(),
        }

        logger.info("ml_error_handler_initialized")

    async def handle_ml_prediction_error(
        self, request: Request, exc: MLPredictionError
    ) -> JSONResponse:
        """
        ML 예측 커스텀 예외 처리

        Args:
            request: FastAPI 요청 객체
            exc: ML 예측 예외

        Returns:
            JSON 에러 응답
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 에러 통계 업데이트
        self._update_error_stats(exc.error_code, str(request.url.path))

        # 구조화된 로깅
        logger.error(
            "ml_prediction_error_occurred",
            request_id=request_id,
            error_code=exc.error_code,
            error_message=exc.message,
            endpoint=str(request.url.path),
            method=request.method,
            details=exc.details,
            http_status_code=exc.http_status_code,
        )

        # 에러 응답 생성
        error_response = create_error_response(
            error_code=ErrorCode(exc.error_code),
            message=exc.message,
            details=exc.details,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=exc.http_status_code, content=error_response.dict()
        )

    async def handle_http_exception(
        self, request: Request, exc: HTTPException
    ) -> JSONResponse:
        """
        HTTP 예외 처리

        Args:
            request: FastAPI 요청 객체
            exc: HTTP 예외

        Returns:
            JSON 에러 응답
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 에러 통계 업데이트
        self._update_error_stats(f"HTTP_{exc.status_code}", str(request.url.path))

        # 로깅
        logger.warning(
            "http_exception_occurred",
            request_id=request_id,
            status_code=exc.status_code,
            detail=exc.detail,
            endpoint=str(request.url.path),
            method=request.method,
        )

        # 기존 detail이 dict인 경우 그대로 반환 (이미 구조화된 에러)
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)

        # 단순 문자열인 경우 구조화된 에러로 변환
        error_response = create_error_response(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=str(exc.detail),
            request_id=request_id,
        )

        return JSONResponse(status_code=exc.status_code, content=error_response.dict())

    async def handle_validation_error(
        self,
        request: Request,
        exc: Union[RequestValidationError, PydanticValidationError],
    ) -> JSONResponse:
        """
        검증 에러 처리

        Args:
            request: FastAPI 요청 객체
            exc: 검증 예외

        Returns:
            JSON 에러 응답
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 에러 통계 업데이트
        self._update_error_stats("VALIDATION_ERROR", str(request.url.path))

        # 검증 에러 상세 정보 추출
        validation_errors = []

        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append(
                ValidationErrorDetail(
                    field=field_path,
                    message=error["msg"],
                    invalid_value=error.get("input"),
                    constraint=error.get("type"),
                )
            )

        # 로깅
        logger.warning(
            "validation_error_occurred",
            request_id=request_id,
            endpoint=str(request.url.path),
            method=request.method,
            validation_errors=[
                {
                    "field": err.field,
                    "message": err.message,
                    "invalid_value": err.invalid_value,
                }
                for err in validation_errors
            ],
        )

        # 검증 에러 응답 생성
        error_response = create_validation_error_response(
            validation_errors=validation_errors, request_id=request_id
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response.dict(),
        )

    async def handle_general_exception(
        self, request: Request, exc: Exception
    ) -> JSONResponse:
        """
        일반 예외 처리

        Args:
            request: FastAPI 요청 객체
            exc: 일반 예외

        Returns:
            JSON 에러 응답
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # 에러 통계 업데이트
        self._update_error_stats("INTERNAL_SERVER_ERROR", str(request.url.path))

        # 상세한 에러 로깅 (스택 트레이스 포함)
        logger.error(
            "unexpected_error_occurred",
            request_id=request_id,
            error_type=type(exc).__name__,
            error_message=str(exc),
            endpoint=str(request.url.path),
            method=request.method,
            traceback=traceback.format_exc(),
        )

        # 프로덕션 환경에서는 상세한 에러 정보 숨김
        import os

        is_production = os.getenv("ENV_MODE", "dev") == "prod"

        if is_production:
            message = "An internal server error occurred"
            details = None
        else:
            message = f"Internal server error: {str(exc)}"
            details = {
                "error_type": type(exc).__name__,
                "traceback": traceback.format_exc().split("\n"),
            }

        # 에러 응답 생성
        error_response = create_error_response(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=message,
            details=details,
            request_id=request_id,
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response.dict(),
        )

    def _update_error_stats(self, error_type: str, endpoint: str) -> None:
        """
        에러 통계 업데이트

        Args:
            error_type: 에러 타입
            endpoint: 엔드포인트 경로
        """
        self.error_stats["total_errors"] += 1

        # 에러 타입별 통계
        if error_type not in self.error_stats["error_by_type"]:
            self.error_stats["error_by_type"][error_type] = 0
        self.error_stats["error_by_type"][error_type] += 1

        # 엔드포인트별 통계
        if endpoint not in self.error_stats["error_by_endpoint"]:
            self.error_stats["error_by_endpoint"][endpoint] = 0
        self.error_stats["error_by_endpoint"][endpoint] += 1

    def get_error_stats(self) -> Dict[str, Any]:
        """
        에러 통계 조회

        Returns:
            에러 통계 정보
        """
        return {
            **self.error_stats,
            "uptime_hours": (
                datetime.now() - self.error_stats["last_reset"]
            ).total_seconds()
            / 3600,
        }

    def reset_error_stats(self) -> None:
        """에러 통계 초기화"""
        self.error_stats = {
            "total_errors": 0,
            "error_by_type": {},
            "error_by_endpoint": {},
            "last_reset": datetime.now(),
        }

        logger.info("error_stats_reset")


# 전역 에러 핸들러 인스턴스
ml_error_handler = MLErrorHandler()


# FastAPI 앱에 등록할 예외 핸들러들
def register_error_handlers(app):
    """
    FastAPI 앱에 에러 핸들러 등록

    Args:
        app: FastAPI 앱 인스턴스
    """

    @app.exception_handler(MLPredictionError)
    async def ml_prediction_error_handler(request: Request, exc: MLPredictionError):
        return await ml_error_handler.handle_ml_prediction_error(request, exc)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return await ml_error_handler.handle_http_exception(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return await ml_error_handler.handle_validation_error(request, exc)

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_error_handler(
        request: Request, exc: PydanticValidationError
    ):
        return await ml_error_handler.handle_validation_error(request, exc)

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return await ml_error_handler.handle_general_exception(request, exc)

    logger.info("ml_error_handlers_registered")


# 에러 로깅을 위한 미들웨어
async def error_logging_middleware(request: Request, call_next):
    """
    에러 로깅 미들웨어

    모든 요청에 대해 request_id를 생성하고 에러 발생 시 추가 정보를 로깅합니다.
    """
    # 요청 ID 생성
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # 요청 시작 로깅
    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        url=str(request.url),
        client_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    start_time = datetime.now()

    try:
        # 요청 처리
        response = await call_next(request)

        # 성공 응답 로깅
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            "request_completed",
            request_id=request_id,
            status_code=response.status_code,
            duration_seconds=duration,
        )

        return response

    except Exception as exc:
        # 예외 발생 시 추가 로깅
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(
            "request_failed_in_middleware",
            request_id=request_id,
            error_type=type(exc).__name__,
            error_message=str(exc),
            duration_seconds=duration,
        )

        # 예외를 다시 발생시켜 에러 핸들러가 처리하도록 함
        raise


# 에러 컨텍스트 매니저
class ErrorContext:
    """
    에러 발생 시 추가 컨텍스트 정보를 제공하는 컨텍스트 매니저
    """

    def __init__(
        self,
        operation: str,
        symbol: Optional[str] = None,
        model_version: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ):
        self.operation = operation
        self.symbol = symbol
        self.model_version = model_version
        self.additional_context = additional_context or {}
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()

        logger.info(
            "operation_started",
            operation=self.operation,
            symbol=self.symbol,
            model_version=self.model_version,
            **self.additional_context,
        )

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type is None:
            # 성공
            logger.info(
                "operation_completed",
                operation=self.operation,
                symbol=self.symbol,
                model_version=self.model_version,
                duration_seconds=duration,
                **self.additional_context,
            )
        else:
            # 실패
            logger.error(
                "operation_failed",
                operation=self.operation,
                symbol=self.symbol,
                model_version=self.model_version,
                duration_seconds=duration,
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None,
                **self.additional_context,
            )

        # 예외를 다시 발생시키지 않음 (False 반환)
        return False


# 에러 발생 시 알림을 위한 헬퍼 함수들
def should_send_alert(error_code: str, endpoint: str) -> bool:
    """
    에러 발생 시 알림을 보낼지 결정

    Args:
        error_code: 에러 코드
        endpoint: 엔드포인트

    Returns:
        알림 전송 여부
    """
    # 심각한 에러들에 대해서만 알림 전송
    critical_errors = [
        "MODEL_TRAINING_FAILED",
        "DATA_SOURCE_UNAVAILABLE",
        "RESOURCE_LIMIT_EXCEEDED",
        "INTERNAL_SERVER_ERROR",
    ]

    return error_code in critical_errors


async def send_error_alert(
    error_code: str, message: str, details: Dict[str, Any], request_id: str
) -> None:
    """
    에러 알림 전송

    Args:
        error_code: 에러 코드
        message: 에러 메시지
        details: 에러 상세 정보
        request_id: 요청 ID
    """
    try:
        # 실제 알림 시스템과 연동 (예: Slack, 이메일 등)
        # 여기서는 로깅으로 대체
        logger.critical(
            "critical_error_alert",
            error_code=error_code,
            message=message,
            details=details,
            request_id=request_id,
            alert_sent=True,
        )

    except Exception as e:
        logger.error(
            "error_alert_send_failed",
            error=str(e),
            original_error_code=error_code,
            request_id=request_id,
        )

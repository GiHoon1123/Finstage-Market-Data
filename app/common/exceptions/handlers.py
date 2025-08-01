"""
에러 핸들링 데코레이터 및 유틸리티

표준화된 에러 처리를 위한 데코레이터와 헬퍼 함수들
"""

import traceback
from functools import wraps
from typing import Type, Callable, Any, Optional, Dict, Union
from sqlalchemy.exc import SQLAlchemyError
import requests
import aiohttp

from app.common.exceptions.base import (
    FinstageException,
    DatabaseError,
    APIError,
    DataError,
    AnalysisError,
    NotificationError,
    SchedulerError,
    ErrorCode,
)
from app.common.utils.logging_config import get_logger


def handle_errors(
    default_exception: Type[FinstageException] = FinstageException,
    reraise: bool = True,
    return_on_error: Any = None,
    log_errors: bool = True,
):
    """
    에러 핸들링 데코레이터

    Args:
        default_exception: 기본 예외 클래스
        reraise: 예외를 다시 발생시킬지 여부
        return_on_error: 에러 발생 시 반환할 값
        log_errors: 에러 로깅 여부
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            try:
                return func(*args, **kwargs)

            except FinstageException:
                # 이미 처리된 커스텀 예외는 그대로 전달
                raise

            except SQLAlchemyError as e:
                error = DatabaseError(
                    message=f"데이터베이스 오류가 발생했습니다: {str(e)}",
                    error_code=ErrorCode.DATABASE_QUERY_ERROR,
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                    original_exception=e,
                )

                if log_errors:
                    logger.error(
                        "database_error_occurred",
                        function=func.__name__,
                        error_code=error.error_code.value,
                        error_message=error.message,
                        original_error=str(e),
                        traceback=traceback.format_exc(),
                    )

                if reraise:
                    raise error
                return return_on_error

            except (requests.RequestException, aiohttp.ClientError) as e:
                error = APIError(
                    message=f"외부 API 호출 중 오류가 발생했습니다: {str(e)}",
                    error_code=ErrorCode.API_CONNECTION_ERROR,
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                    original_exception=e,
                )

                if log_errors:
                    logger.error(
                        "api_error_occurred",
                        function=func.__name__,
                        error_code=error.error_code.value,
                        error_message=error.message,
                        original_error=str(e),
                        traceback=traceback.format_exc(),
                    )

                if reraise:
                    raise error
                return return_on_error

            except Exception as e:
                error = default_exception(
                    message=f"예상치 못한 오류가 발생했습니다: {str(e)}",
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                        "exception_type": type(e).__name__,
                    },
                    original_exception=e,
                )

                if log_errors:
                    logger.error(
                        "unexpected_error_occurred",
                        function=func.__name__,
                        error_code=error.error_code.value,
                        error_message=error.message,
                        exception_type=type(e).__name__,
                        original_error=str(e),
                        traceback=traceback.format_exc(),
                    )

                if reraise:
                    raise error
                return return_on_error

        return wrapper

    return decorator


def handle_async_errors(
    default_exception: Type[FinstageException] = FinstageException,
    reraise: bool = True,
    return_on_error: Any = None,
    log_errors: bool = True,
):
    """
    비동기 함수용 에러 핸들링 데코레이터
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            try:
                return await func(*args, **kwargs)

            except FinstageException:
                # 이미 처리된 커스텀 예외는 그대로 전달
                raise

            except SQLAlchemyError as e:
                error = DatabaseError(
                    message=f"데이터베이스 오류가 발생했습니다: {str(e)}",
                    error_code=ErrorCode.DATABASE_QUERY_ERROR,
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                    original_exception=e,
                )

                if log_errors:
                    logger.error(
                        "database_error_occurred",
                        function=func.__name__,
                        error_code=error.error_code.value,
                        error_message=error.message,
                        original_error=str(e),
                        traceback=traceback.format_exc(),
                    )

                if reraise:
                    raise error
                return return_on_error

            except (requests.RequestException, aiohttp.ClientError) as e:
                error = APIError(
                    message=f"외부 API 호출 중 오류가 발생했습니다: {str(e)}",
                    error_code=ErrorCode.API_CONNECTION_ERROR,
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                    },
                    original_exception=e,
                )

                if log_errors:
                    logger.error(
                        "api_error_occurred",
                        function=func.__name__,
                        error_code=error.error_code.value,
                        error_message=error.message,
                        original_error=str(e),
                        traceback=traceback.format_exc(),
                    )

                if reraise:
                    raise error
                return return_on_error

            except Exception as e:
                error = default_exception(
                    message=f"예상치 못한 오류가 발생했습니다: {str(e)}",
                    details={
                        "function": func.__name__,
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                        "exception_type": type(e).__name__,
                    },
                    original_exception=e,
                )

                if log_errors:
                    logger.error(
                        "unexpected_error_occurred",
                        function=func.__name__,
                        error_code=error.error_code.value,
                        error_message=error.message,
                        exception_type=type(e).__name__,
                        original_error=str(e),
                        traceback=traceback.format_exc(),
                    )

                if reraise:
                    raise error
                return return_on_error

        return wrapper

    return decorator


# 특정 도메인별 에러 핸들러들
def handle_database_errors(reraise: bool = True, return_on_error: Any = None):
    """데이터베이스 관련 에러 핸들러"""
    return handle_errors(
        default_exception=DatabaseError,
        reraise=reraise,
        return_on_error=return_on_error,
    )


def handle_api_errors(reraise: bool = True, return_on_error: Any = None):
    """API 관련 에러 핸들러"""
    return handle_errors(
        default_exception=APIError, reraise=reraise, return_on_error=return_on_error
    )


def handle_analysis_errors(reraise: bool = True, return_on_error: Any = None):
    """기술적 분석 관련 에러 핸들러"""
    return handle_errors(
        default_exception=AnalysisError,
        reraise=reraise,
        return_on_error=return_on_error,
    )


def handle_notification_errors(reraise: bool = True, return_on_error: Any = None):
    """알림 관련 에러 핸들러"""
    return handle_errors(
        default_exception=NotificationError,
        reraise=reraise,
        return_on_error=return_on_error,
    )


def handle_scheduler_errors(reraise: bool = True, return_on_error: Any = None):
    """스케줄러 관련 에러 핸들러"""
    return handle_errors(
        default_exception=SchedulerError,
        reraise=reraise,
        return_on_error=return_on_error,
    )


# 유틸리티 함수들
def safe_execute(
    func: Callable, *args, default_return: Any = None, log_errors: bool = True, **kwargs
) -> Any:
    """
    안전한 함수 실행

    에러가 발생해도 애플리케이션이 중단되지 않도록 보장
    """
    logger = get_logger("safe_execute")

    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(
                "safe_execute_failed",
                function=func.__name__,
                error=str(e),
                args=str(args)[:200],
                kwargs=str(kwargs)[:200],
            )
        return default_return


def create_error_response(
    error: Union[FinstageException, Exception], include_traceback: bool = False
) -> Dict[str, Any]:
    """
    에러 응답 생성

    API 응답이나 결과 딕셔너리에 사용할 표준화된 에러 정보 생성
    """
    if isinstance(error, FinstageException):
        response = error.to_dict()
    else:
        response = {
            "error_code": ErrorCode.UNKNOWN_ERROR.value,
            "message": str(error),
            "details": {"exception_type": type(error).__name__},
            "original_error": str(error),
        }

    if include_traceback:
        response["traceback"] = traceback.format_exc()

    return response


def log_error_context(logger, error: Exception, context: Dict[str, Any] = None) -> None:
    """
    에러 컨텍스트 로깅

    에러 발생 시 추가 컨텍스트 정보와 함께 로깅
    """
    context = context or {}

    if isinstance(error, FinstageException):
        logger.error(
            "finstage_error_occurred",
            error_code=error.error_code.value,
            error_message=error.message,
            error_details=error.details,
            original_error=(
                str(error.original_exception) if error.original_exception else None
            ),
            **context,
        )
    else:
        logger.error(
            "unexpected_error_occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            traceback=traceback.format_exc(),
            **context,
        )

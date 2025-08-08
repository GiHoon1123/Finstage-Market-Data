"""
ML 예측 전용 예외 클래스

이 파일은 ML 예측 시스템에서 사용하는 커스텀 예외 클래스들을 정의합니다.
각 예외는 적절한 HTTP 상태 코드와 에러 메시지를 포함합니다.

주요 예외 카테고리:
- 모델 관련 예외
- 데이터 관련 예외
- 예측 관련 예외
- 훈련 관련 예외
"""

from typing import Optional, Dict, Any
from fastapi import status


class MLPredictionError(Exception):
    """
    ML 예측 시스템 기본 예외 클래스

    모든 ML 관련 예외의 부모 클래스입니다.
    """

    def __init__(
        self,
        message: str,
        error_code: str = "ML_ERROR",
        http_status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.http_status_code = http_status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "http_status_code": self.http_status_code,
        }


# 모델 관련 예외들
class ModelNotFoundError(MLPredictionError):
    """모델을 찾을 수 없는 경우"""

    def __init__(
        self,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        symbol: Optional[str] = None,
        message: Optional[str] = None,
    ):
        if not message:
            if model_name and model_version:
                message = f"Model {model_name} version {model_version} not found"
            elif symbol:
                message = f"No active model found for symbol {symbol}"
            else:
                message = "Model not found"

        details = {}
        if model_name:
            details["model_name"] = model_name
        if model_version:
            details["model_version"] = model_version
        if symbol:
            details["symbol"] = symbol

        super().__init__(
            message=message,
            error_code="MODEL_NOT_FOUND",
            http_status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ModelTrainingError(MLPredictionError):
    """모델 훈련 실패"""

    def __init__(
        self,
        symbol: str,
        message: Optional[str] = None,
        training_error: Optional[str] = None,
        epoch: Optional[int] = None,
    ):
        if not message:
            message = f"Model training failed for symbol {symbol}"

        details = {"symbol": symbol}
        if training_error:
            details["training_error"] = training_error
        if epoch is not None:
            details["failed_at_epoch"] = epoch

        super().__init__(
            message=message,
            error_code="MODEL_TRAINING_FAILED",
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ModelLoadingError(MLPredictionError):
    """모델 로딩 실패"""

    def __init__(
        self,
        model_path: str,
        message: Optional[str] = None,
        loading_error: Optional[str] = None,
    ):
        if not message:
            message = f"Failed to load model from {model_path}"

        details = {"model_path": model_path}
        if loading_error:
            details["loading_error"] = loading_error

        super().__init__(
            message=message,
            error_code="MODEL_LOADING_FAILED",
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ModelAlreadyExistsError(MLPredictionError):
    """모델이 이미 존재하는 경우"""

    def __init__(
        self, model_name: str, model_version: str, message: Optional[str] = None
    ):
        if not message:
            message = f"Model {model_name} version {model_version} already exists"

        super().__init__(
            message=message,
            error_code="MODEL_ALREADY_EXISTS",
            http_status_code=status.HTTP_409_CONFLICT,
            details={"model_name": model_name, "model_version": model_version},
        )


class NoActiveModelError(MLPredictionError):
    """활성 모델이 없는 경우"""

    def __init__(
        self, symbol: str, model_type: str = "lstm", message: Optional[str] = None
    ):
        if not message:
            message = f"No active {model_type} model found for symbol {symbol}"

        super().__init__(
            message=message,
            error_code="NO_ACTIVE_MODEL",
            http_status_code=status.HTTP_404_NOT_FOUND,
            details={"symbol": symbol, "model_type": model_type},
        )


# 데이터 관련 예외들
class DataNotFoundError(MLPredictionError):
    """필요한 데이터를 찾을 수 없는 경우"""

    def __init__(
        self,
        symbol: str,
        data_type: str = "price_data",
        date_range: Optional[Dict[str, str]] = None,
        message: Optional[str] = None,
    ):
        if not message:
            message = f"Required {data_type} not found for symbol {symbol}"

        details = {"symbol": symbol, "data_type": data_type}
        if date_range:
            details["date_range"] = date_range

        super().__init__(
            message=message,
            error_code="DATA_NOT_FOUND",
            http_status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class InsufficientDataError(MLPredictionError):
    """데이터가 부족한 경우"""

    def __init__(
        self,
        symbol: str,
        required_count: int,
        available_count: int,
        data_type: str = "price_data",
        message: Optional[str] = None,
    ):
        if not message:
            message = f"Insufficient {data_type} for {symbol}: need {required_count}, got {available_count}"

        super().__init__(
            message=message,
            error_code="INSUFFICIENT_DATA",
            http_status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "symbol": symbol,
                "data_type": data_type,
                "required_count": required_count,
                "available_count": available_count,
            },
        )


class DataQualityError(MLPredictionError):
    """데이터 품질 문제"""

    def __init__(
        self, symbol: str, quality_issues: Dict[str, Any], message: Optional[str] = None
    ):
        if not message:
            message = f"Data quality issues detected for symbol {symbol}"

        super().__init__(
            message=message,
            error_code="DATA_QUALITY_ERROR",
            http_status_code=status.HTTP_400_BAD_REQUEST,
            details={"symbol": symbol, "quality_issues": quality_issues},
        )


class DataSourceUnavailableError(MLPredictionError):
    """데이터 소스를 사용할 수 없는 경우"""

    def __init__(
        self,
        data_source: str,
        message: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        if not message:
            message = f"Data source {data_source} is currently unavailable"

        details = {"data_source": data_source}
        if retry_after:
            details["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            error_code="DATA_SOURCE_UNAVAILABLE",
            http_status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


# 예측 관련 예외들
class PredictionError(MLPredictionError):
    """예측 실행 실패"""

    def __init__(
        self,
        symbol: str,
        model_version: Optional[str] = None,
        prediction_error: Optional[str] = None,
        message: Optional[str] = None,
    ):
        if not message:
            message = f"Prediction failed for symbol {symbol}"

        details = {"symbol": symbol}
        if model_version:
            details["model_version"] = model_version
        if prediction_error:
            details["prediction_error"] = prediction_error

        super().__init__(
            message=message,
            error_code="PREDICTION_FAILED",
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class InvalidTimeframeError(MLPredictionError):
    """잘못된 타임프레임"""

    def __init__(
        self, timeframe: str, valid_timeframes: list, message: Optional[str] = None
    ):
        if not message:
            message = (
                f"Invalid timeframe '{timeframe}'. Valid options: {valid_timeframes}"
            )

        super().__init__(
            message=message,
            error_code="INVALID_TIMEFRAME",
            http_status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "invalid_timeframe": timeframe,
                "valid_timeframes": valid_timeframes,
            },
        )


class InvalidSymbolError(MLPredictionError):
    """잘못된 심볼"""

    def __init__(self, symbol: str, message: Optional[str] = None):
        if not message:
            message = f"Invalid symbol: {symbol}"

        super().__init__(
            message=message,
            error_code="INVALID_SYMBOL",
            http_status_code=status.HTTP_400_BAD_REQUEST,
            details={"invalid_symbol": symbol},
        )


class InvalidDateRangeError(MLPredictionError):
    """잘못된 날짜 범위"""

    def __init__(self, start_date: str, end_date: str, message: Optional[str] = None):
        if not message:
            message = f"Invalid date range: {start_date} to {end_date}"

        super().__init__(
            message=message,
            error_code="INVALID_DATE_RANGE",
            http_status_code=status.HTTP_400_BAD_REQUEST,
            details={"start_date": start_date, "end_date": end_date},
        )


# 백테스트 관련 예외들
class BacktestError(MLPredictionError):
    """백테스트 실행 실패"""

    def __init__(
        self,
        symbol: str,
        model_version: str,
        backtest_error: Optional[str] = None,
        message: Optional[str] = None,
    ):
        if not message:
            message = f"Backtest failed for {symbol} with model {model_version}"

        details = {"symbol": symbol, "model_version": model_version}
        if backtest_error:
            details["backtest_error"] = backtest_error

        super().__init__(
            message=message,
            error_code="BACKTEST_FAILED",
            http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class InvalidBacktestConfigError(MLPredictionError):
    """잘못된 백테스트 설정"""

    def __init__(self, config_errors: Dict[str, str], message: Optional[str] = None):
        if not message:
            message = "Invalid backtest configuration"

        super().__init__(
            message=message,
            error_code="INVALID_BACKTEST_CONFIG",
            http_status_code=status.HTTP_400_BAD_REQUEST,
            details={"config_errors": config_errors},
        )


# 리소스 관련 예외들
class ResourceLimitExceededError(MLPredictionError):
    """리소스 한계 초과"""

    def __init__(
        self,
        resource_type: str,
        current_usage: float,
        limit: float,
        message: Optional[str] = None,
    ):
        if not message:
            message = f"{resource_type} limit exceeded: {current_usage}/{limit}"

        super().__init__(
            message=message,
            error_code="RESOURCE_LIMIT_EXCEEDED",
            http_status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={
                "resource_type": resource_type,
                "current_usage": current_usage,
                "limit": limit,
            },
        )


class TimeoutError(MLPredictionError):
    """작업 타임아웃"""

    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        elapsed_seconds: Optional[float] = None,
        message: Optional[str] = None,
    ):
        if not message:
            message = (
                f"Operation '{operation}' timed out after {timeout_seconds} seconds"
            )

        details = {"operation": operation, "timeout_seconds": timeout_seconds}
        if elapsed_seconds is not None:
            details["elapsed_seconds"] = elapsed_seconds

        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            http_status_code=status.HTTP_408_REQUEST_TIMEOUT,
            details=details,
        )


# 검증 관련 예외들
class ValidationError(MLPredictionError):
    """입력 검증 실패"""

    def __init__(self, field_errors: Dict[str, str], message: Optional[str] = None):
        if not message:
            message = "Request validation failed"

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            http_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details={"field_errors": field_errors},
        )


# 권한 관련 예외들
class UnauthorizedError(MLPredictionError):
    """인증 실패"""

    def __init__(self, message: Optional[str] = None):
        if not message:
            message = "Authentication required"

        super().__init__(
            message=message,
            error_code="UNAUTHORIZED",
            http_status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(MLPredictionError):
    """권한 없음"""

    def __init__(self, resource: str, action: str, message: Optional[str] = None):
        if not message:
            message = f"Access forbidden: cannot {action} {resource}"

        super().__init__(
            message=message,
            error_code="FORBIDDEN",
            http_status_code=status.HTTP_403_FORBIDDEN,
            details={"resource": resource, "action": action},
        )


# 예외 매핑 딕셔너리 (에러 코드 -> 예외 클래스)
EXCEPTION_MAPPING = {
    "MODEL_NOT_FOUND": ModelNotFoundError,
    "MODEL_TRAINING_FAILED": ModelTrainingError,
    "MODEL_LOADING_FAILED": ModelLoadingError,
    "MODEL_ALREADY_EXISTS": ModelAlreadyExistsError,
    "NO_ACTIVE_MODEL": NoActiveModelError,
    "DATA_NOT_FOUND": DataNotFoundError,
    "INSUFFICIENT_DATA": InsufficientDataError,
    "DATA_QUALITY_ERROR": DataQualityError,
    "DATA_SOURCE_UNAVAILABLE": DataSourceUnavailableError,
    "PREDICTION_FAILED": PredictionError,
    "INVALID_TIMEFRAME": InvalidTimeframeError,
    "INVALID_SYMBOL": InvalidSymbolError,
    "INVALID_DATE_RANGE": InvalidDateRangeError,
    "BACKTEST_FAILED": BacktestError,
    "INVALID_BACKTEST_CONFIG": InvalidBacktestConfigError,
    "RESOURCE_LIMIT_EXCEEDED": ResourceLimitExceededError,
    "TIMEOUT_ERROR": TimeoutError,
    "VALIDATION_ERROR": ValidationError,
    "UNAUTHORIZED": UnauthorizedError,
    "FORBIDDEN": ForbiddenError,
}


def create_exception_from_error_code(
    error_code: str, message: str, details: Optional[Dict[str, Any]] = None
) -> MLPredictionError:
    """
    에러 코드로부터 적절한 예외 인스턴스 생성

    Args:
        error_code: 에러 코드
        message: 에러 메시지
        details: 에러 상세 정보

    Returns:
        적절한 예외 인스턴스
    """
    exception_class = EXCEPTION_MAPPING.get(error_code, MLPredictionError)

    try:
        # 예외 클래스의 생성자에 맞게 인스턴스 생성 시도
        if error_code == "MODEL_NOT_FOUND" and details:
            return exception_class(
                model_name=details.get("model_name"),
                model_version=details.get("model_version"),
                symbol=details.get("symbol"),
                message=message,
            )
        elif error_code in ["DATA_NOT_FOUND", "PREDICTION_FAILED"] and details:
            return exception_class(
                symbol=details.get("symbol", "unknown"), message=message
            )
        else:
            # 기본 생성자 사용
            return exception_class(message)

    except Exception:
        # 생성자 호출 실패 시 기본 예외 반환
        return MLPredictionError(
            message=message, error_code=error_code, details=details
        )

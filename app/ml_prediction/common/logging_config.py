"""
ML 예측 전용 로깅 설정

이 파일은 ML 예측 시스템의 전용 로깅 설정을 구현합니다.
구조화된 로깅, 성능 추적, 모델 훈련/예측 과정 로깅 등을 제공합니다.

주요 기능:
- 구조화된 JSON 로깅
- 성능 메트릭 로깅
- 모델 라이프사이클 로깅
- 예측 결과 로깅
"""

import logging
import json
import time
from typing import Dict, Any, Optional, Union
from datetime import datetime
from functools import wraps
from contextlib import contextmanager

from app.common.utils.logging_config import get_logger


class MLStructuredLogger:
    """
    ML 예측 전용 구조화된 로거

    ML 관련 이벤트를 구조화된 형태로 로깅합니다.
    """

    def __init__(self, name: str):
        """
        로거 초기화

        Args:
            name: 로거 이름
        """
        self.logger = get_logger(name)
        self.name = name

    def log_model_training_start(
        self, symbol: str, training_config: Dict[str, Any], data_info: Dict[str, Any]
    ) -> None:
        """
        모델 훈련 시작 로깅

        Args:
            symbol: 심볼
            training_config: 훈련 설정
            data_info: 데이터 정보
        """
        self.logger.info(
            "model_training_started",
            event_type="model_training",
            phase="start",
            symbol=symbol,
            training_config=training_config,
            data_info=data_info,
            timestamp=datetime.now().isoformat(),
        )

    def log_model_training_progress(
        self,
        symbol: str,
        epoch: int,
        total_epochs: int,
        loss: float,
        val_loss: float,
        metrics: Dict[str, float],
    ) -> None:
        """
        모델 훈련 진행 상황 로깅

        Args:
            symbol: 심볼
            epoch: 현재 에포크
            total_epochs: 총 에포크 수
            loss: 훈련 손실
            val_loss: 검증 손실
            metrics: 추가 메트릭
        """
        progress_percent = (epoch / total_epochs) * 100

        self.logger.info(
            "model_training_progress",
            event_type="model_training",
            phase="progress",
            symbol=symbol,
            epoch=epoch,
            total_epochs=total_epochs,
            progress_percent=progress_percent,
            loss=loss,
            val_loss=val_loss,
            metrics=metrics,
            timestamp=datetime.now().isoformat(),
        )

    def log_model_training_complete(
        self,
        symbol: str,
        model_version: str,
        training_duration: float,
        final_metrics: Dict[str, float],
        model_path: str,
    ) -> None:
        """
        모델 훈련 완료 로깅

        Args:
            symbol: 심볼
            model_version: 모델 버전
            training_duration: 훈련 소요 시간 (초)
            final_metrics: 최종 메트릭
            model_path: 모델 저장 경로
        """
        self.logger.info(
            "model_training_completed",
            event_type="model_training",
            phase="complete",
            symbol=symbol,
            model_version=model_version,
            training_duration_seconds=training_duration,
            final_metrics=final_metrics,
            model_path=model_path,
            timestamp=datetime.now().isoformat(),
        )

    def log_prediction_request(
        self,
        symbol: str,
        model_version: str,
        prediction_config: Dict[str, Any],
        request_id: str,
    ) -> None:
        """
        예측 요청 로깅

        Args:
            symbol: 심볼
            model_version: 모델 버전
            prediction_config: 예측 설정
            request_id: 요청 ID
        """
        self.logger.info(
            "prediction_request_received",
            event_type="prediction",
            phase="request",
            symbol=symbol,
            model_version=model_version,
            prediction_config=prediction_config,
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
        )

    def log_prediction_result(
        self,
        symbol: str,
        model_version: str,
        predictions: Dict[str, Any],
        confidence_scores: Dict[str, float],
        processing_time: float,
        request_id: str,
    ) -> None:
        """
        예측 결과 로깅

        Args:
            symbol: 심볼
            model_version: 모델 버전
            predictions: 예측 결과
            confidence_scores: 신뢰도 점수
            processing_time: 처리 시간 (초)
            request_id: 요청 ID
        """
        self.logger.info(
            "prediction_completed",
            event_type="prediction",
            phase="complete",
            symbol=symbol,
            model_version=model_version,
            predictions=predictions,
            confidence_scores=confidence_scores,
            processing_time_seconds=processing_time,
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
        )

    def log_model_evaluation(
        self,
        symbol: str,
        model_version: str,
        evaluation_period: Dict[str, str],
        performance_metrics: Dict[str, Any],
        evaluation_duration: float,
    ) -> None:
        """
        모델 평가 로깅

        Args:
            symbol: 심볼
            model_version: 모델 버전
            evaluation_period: 평가 기간
            performance_metrics: 성능 메트릭
            evaluation_duration: 평가 소요 시간 (초)
        """
        self.logger.info(
            "model_evaluation_completed",
            event_type="model_evaluation",
            symbol=symbol,
            model_version=model_version,
            evaluation_period=evaluation_period,
            performance_metrics=performance_metrics,
            evaluation_duration_seconds=evaluation_duration,
            timestamp=datetime.now().isoformat(),
        )

    def log_backtest_result(
        self,
        symbol: str,
        model_version: str,
        backtest_config: Dict[str, Any],
        performance_summary: Dict[str, float],
        trade_count: int,
        backtest_duration: float,
    ) -> None:
        """
        백테스트 결과 로깅

        Args:
            symbol: 심볼
            model_version: 모델 버전
            backtest_config: 백테스트 설정
            performance_summary: 성능 요약
            trade_count: 거래 횟수
            backtest_duration: 백테스트 소요 시간 (초)
        """
        self.logger.info(
            "backtest_completed",
            event_type="backtest",
            symbol=symbol,
            model_version=model_version,
            backtest_config=backtest_config,
            performance_summary=performance_summary,
            trade_count=trade_count,
            backtest_duration_seconds=backtest_duration,
            timestamp=datetime.now().isoformat(),
        )

    def log_data_processing(
        self,
        symbol: str,
        operation: str,
        data_stats: Dict[str, Any],
        processing_time: float,
    ) -> None:
        """
        데이터 처리 로깅

        Args:
            symbol: 심볼
            operation: 처리 작업
            data_stats: 데이터 통계
            processing_time: 처리 시간 (초)
        """
        self.logger.info(
            "data_processing_completed",
            event_type="data_processing",
            symbol=symbol,
            operation=operation,
            data_stats=data_stats,
            processing_time_seconds=processing_time,
            timestamp=datetime.now().isoformat(),
        )

    def log_performance_metrics(
        self,
        operation: str,
        metrics: Dict[str, Union[float, int]],
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        성능 메트릭 로깅

        Args:
            operation: 작업명
            metrics: 성능 메트릭
            context: 추가 컨텍스트
        """
        self.logger.info(
            "performance_metrics",
            event_type="performance",
            operation=operation,
            metrics=metrics,
            context=context or {},
            timestamp=datetime.now().isoformat(),
        )

    def log_resource_usage(
        self,
        operation: str,
        resource_usage: Dict[str, float],
        thresholds: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        리소스 사용량 로깅

        Args:
            operation: 작업명
            resource_usage: 리소스 사용량
            thresholds: 임계값
        """
        # 임계값 초과 여부 확인
        alerts = {}
        if thresholds:
            for resource, usage in resource_usage.items():
                threshold = thresholds.get(resource)
                if threshold and usage > threshold:
                    alerts[resource] = {
                        "usage": usage,
                        "threshold": threshold,
                        "exceeded_by": usage - threshold,
                    }

        log_level = logging.WARNING if alerts else logging.INFO

        self.logger.log(
            log_level,
            "resource_usage_monitored",
            event_type="resource_monitoring",
            operation=operation,
            resource_usage=resource_usage,
            thresholds=thresholds,
            alerts=alerts,
            timestamp=datetime.now().isoformat(),
        )


# 성능 측정 데코레이터
def log_performance(
    operation: str,
    logger_name: str = "ml_prediction.performance",
    include_args: bool = False,
    include_result: bool = False,
):
    """
    함수 성능을 측정하고 로깅하는 데코레이터

    Args:
        operation: 작업명
        logger_name: 로거 이름
        include_args: 함수 인자 포함 여부
        include_result: 함수 결과 포함 여부
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = MLStructuredLogger(logger_name)
            start_time = time.time()

            context = {"function": func.__name__}
            if include_args:
                context["args"] = str(args)[:200]  # 길이 제한
                context["kwargs"] = {k: str(v)[:100] for k, v in kwargs.items()}

            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                metrics = {"duration_seconds": duration, "status": "success"}

                if include_result and result is not None:
                    context["result_type"] = type(result).__name__
                    if hasattr(result, "__len__"):
                        context["result_size"] = len(result)

                logger.log_performance_metrics(operation, metrics, context)
                return result

            except Exception as e:
                duration = time.time() - start_time

                metrics = {"duration_seconds": duration, "status": "error"}

                context["error"] = str(e)
                context["error_type"] = type(e).__name__

                logger.log_performance_metrics(operation, metrics, context)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = MLStructuredLogger(logger_name)
            start_time = time.time()

            context = {"function": func.__name__}
            if include_args:
                context["args"] = str(args)[:200]
                context["kwargs"] = {k: str(v)[:100] for k, v in kwargs.items()}

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                metrics = {"duration_seconds": duration, "status": "success"}

                if include_result and result is not None:
                    context["result_type"] = type(result).__name__
                    if hasattr(result, "__len__"):
                        context["result_size"] = len(result)

                logger.log_performance_metrics(operation, metrics, context)
                return result

            except Exception as e:
                duration = time.time() - start_time

                metrics = {"duration_seconds": duration, "status": "error"}

                context["error"] = str(e)
                context["error_type"] = type(e).__name__

                logger.log_performance_metrics(operation, metrics, context)
                raise

        # 비동기 함수인지 확인
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 컨텍스트 매니저를 사용한 로깅
@contextmanager
def log_operation(
    operation: str, logger_name: str = "ml_prediction.operations", **context
):
    """
    작업 실행을 로깅하는 컨텍스트 매니저

    Args:
        operation: 작업명
        logger_name: 로거 이름
        **context: 추가 컨텍스트
    """
    logger = MLStructuredLogger(logger_name)
    start_time = time.time()

    # 작업 시작 로깅
    logger.logger.info(
        "operation_started",
        operation=operation,
        context=context,
        timestamp=datetime.now().isoformat(),
    )

    try:
        yield logger

        # 작업 성공 로깅
        duration = time.time() - start_time
        logger.logger.info(
            "operation_completed",
            operation=operation,
            duration_seconds=duration,
            status="success",
            context=context,
            timestamp=datetime.now().isoformat(),
        )

    except Exception as e:
        # 작업 실패 로깅
        duration = time.time() - start_time
        logger.logger.error(
            "operation_failed",
            operation=operation,
            duration_seconds=duration,
            status="error",
            error=str(e),
            error_type=type(e).__name__,
            context=context,
            timestamp=datetime.now().isoformat(),
        )
        raise


# 배치 작업 로깅
class BatchOperationLogger:
    """
    배치 작업 전용 로거

    여러 항목을 처리하는 배치 작업의 진행 상황을 로깅합니다.
    """

    def __init__(
        self, operation: str, total_items: int, logger_name: str = "ml_prediction.batch"
    ):
        self.operation = operation
        self.total_items = total_items
        self.logger = MLStructuredLogger(logger_name)
        self.start_time = time.time()
        self.processed_items = 0
        self.successful_items = 0
        self.failed_items = 0
        self.errors = []

    def log_start(self, **context) -> None:
        """배치 작업 시작 로깅"""
        self.logger.logger.info(
            "batch_operation_started",
            operation=self.operation,
            total_items=self.total_items,
            context=context,
            timestamp=datetime.now().isoformat(),
        )

    def log_item_processed(
        self, item_id: str, success: bool, error: Optional[str] = None, **item_context
    ) -> None:
        """개별 항목 처리 결과 로깅"""
        self.processed_items += 1

        if success:
            self.successful_items += 1
        else:
            self.failed_items += 1
            if error:
                self.errors.append({"item_id": item_id, "error": error})

        # 진행률 계산
        progress_percent = (self.processed_items / self.total_items) * 100

        # 주기적으로 진행 상황 로깅 (10% 단위)
        if self.processed_items % max(1, self.total_items // 10) == 0:
            self.logger.logger.info(
                "batch_operation_progress",
                operation=self.operation,
                processed_items=self.processed_items,
                total_items=self.total_items,
                progress_percent=progress_percent,
                successful_items=self.successful_items,
                failed_items=self.failed_items,
                timestamp=datetime.now().isoformat(),
            )

    def log_complete(self, **context) -> None:
        """배치 작업 완료 로깅"""
        duration = time.time() - self.start_time
        success_rate = (
            (self.successful_items / self.total_items) * 100
            if self.total_items > 0
            else 0
        )

        self.logger.logger.info(
            "batch_operation_completed",
            operation=self.operation,
            total_items=self.total_items,
            processed_items=self.processed_items,
            successful_items=self.successful_items,
            failed_items=self.failed_items,
            success_rate_percent=success_rate,
            duration_seconds=duration,
            errors=self.errors[:10],  # 최대 10개 에러만 로깅
            context=context,
            timestamp=datetime.now().isoformat(),
        )


# 로거 팩토리 함수들
def get_ml_logger(name: str) -> MLStructuredLogger:
    """ML 구조화 로거 생성"""
    return MLStructuredLogger(f"ml_prediction.{name}")


def get_training_logger() -> MLStructuredLogger:
    """모델 훈련 전용 로거 생성"""
    return MLStructuredLogger("ml_prediction.training")


def get_prediction_logger() -> MLStructuredLogger:
    """예측 전용 로거 생성"""
    return MLStructuredLogger("ml_prediction.prediction")


def get_evaluation_logger() -> MLStructuredLogger:
    """평가 전용 로거 생성"""
    return MLStructuredLogger("ml_prediction.evaluation")


def get_data_logger() -> MLStructuredLogger:
    """데이터 처리 전용 로거 생성"""
    return MLStructuredLogger("ml_prediction.data")

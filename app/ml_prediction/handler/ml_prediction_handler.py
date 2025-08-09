"""
ML 예측 API 핸들러

이 파일은 ML 예측 API의 핸들러를 구현합니다.
요청 검증, 비즈니스 로직 호출, 응답 변환을 담당합니다.

주요 기능:
- 요청 검증 및 변환
- 비즈니스 로직 호출
- 응답 변환 및 에러 처리
- 비동기 처리 지원
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import asyncio
import uuid
from fastapi import HTTPException, status

from app.ml_prediction.service.ml_prediction_service import MLPredictionService
from app.ml_prediction.service.model_management_service import ModelManagementService
from app.ml_prediction.ml.evaluation.backtester import BacktestConfig
from app.ml_prediction.web.dto.request_models import (
    TrainModelRequest,
    PredictionRequest,
    EvaluationRequest,
    BacktestRequest,
)
from app.ml_prediction.web.dto.response_models import (
    TrainModelResponse,
    PredictionResponse,
    EvaluationResponse,
    BacktestResponse,
    ServiceStatusResponse,
    ResponseStatus,
    ModelInfo,
    PredictionResult,
)
from app.ml_prediction.web.dto.error_models import (
    ErrorCode,
    create_error_response,
    ERROR_HTTP_STATUS,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MLPredictionHandler:
    """
    ML 예측 API 핸들러

    API 요청을 처리하고 비즈니스 로직과 연결합니다.
    """

    def __init__(self):
        """핸들러 초기화"""
        try:
            self.ml_service = MLPredictionService()
            self.model_service = ModelManagementService()
            logger.info("ml_prediction_handler_initialized_full_version")
        except Exception as e:
            logger.error("ml_prediction_handler_init_failed", error=str(e))
            # 임시 버전으로 폴백
            self.ml_service = None
            self.model_service = None
            logger.info("ml_prediction_handler_initialized_fallback_version")

    async def train_model(
        self, request: TrainModelRequest, request_id: Optional[str] = None
    ) -> TrainModelResponse:
        """
        모델 훈련 처리

        Args:
            request: 훈련 요청
            request_id: 요청 ID

        Returns:
            훈련 응답

        Raises:
            HTTPException: 훈련 실패 시
        """
        if not self.ml_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ML service not available - dependencies not properly initialized",
            )

        request_id = request_id or str(uuid.uuid4())

        logger.info(
            "train_model_request_received",
            request_id=request_id,
            symbol=request.symbol,
            training_days=request.training_days,
            force_retrain=request.force_retrain,
        )

        try:
            # 비즈니스 로직 호출
            result = await self.ml_service.train_model(
                symbol=request.symbol,
                training_days=request.training_days,
                validation_split=request.validation_split,
                force_retrain=request.force_retrain,
            )

            # 응답 변환
            if result["status"] == "success":
                model_info = ModelInfo(
                    model_id=result.get("model_id"),
                    model_name=result["model_name"],
                    model_version=result["model_version"],
                    model_type=result.get("model_type", "lstm"),
                    symbol=request.symbol,
                    is_active=result.get("is_active", True),
                    training_date=result.get("training_end_date"),
                    created_at=result.get("created_at", datetime.now().isoformat()),
                )

                return TrainModelResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Model training completed successfully",
                    timestamp=datetime.now().isoformat(),
                    model_info=model_info,
                    training_metrics=result.get("training_metrics"),
                    initial_evaluation=result.get("initial_evaluation"),
                )

            elif result["status"] == "skipped":
                existing_model = result.get("existing_model", {})
                model_info = ModelInfo(
                    model_name=existing_model.get("model_name", ""),
                    model_version=existing_model.get("model_version", ""),
                    model_type=existing_model.get("model_type", "lstm"),
                    symbol=request.symbol,
                    is_active=existing_model.get("is_active", True),
                    training_date=existing_model.get("training_date"),
                    created_at=existing_model.get(
                        "created_at", datetime.now().isoformat()
                    ),
                )

                return TrainModelResponse(
                    status=ResponseStatus.SKIPPED,
                    message=result.get("message", "Training skipped"),
                    timestamp=datetime.now().isoformat(),
                    existing_model=model_info,
                )

            else:
                # 훈련 실패
                error_response = create_error_response(
                    error_code=ErrorCode.MODEL_TRAINING_FAILED,
                    message=result.get("error", "Model training failed"),
                    request_id=request_id,
                )

                raise HTTPException(
                    status_code=ERROR_HTTP_STATUS[ErrorCode.MODEL_TRAINING_FAILED],
                    detail=error_response.dict(),
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "train_model_handler_error",
                request_id=request_id,
                symbol=request.symbol,
                error=str(e),
            )

            error_response = create_error_response(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Training failed: {str(e)}",
                request_id=request_id,
            )

            raise HTTPException(
                status_code=ERROR_HTTP_STATUS[ErrorCode.INTERNAL_SERVER_ERROR],
                detail=error_response.dict(),
            )

    async def predict_prices(
        self, request: PredictionRequest, request_id: Optional[str] = None
    ) -> PredictionResponse:
        """
        가격 예측 처리

        Args:
            request: 예측 요청
            request_id: 요청 ID

        Returns:
            예측 응답

        Raises:
            HTTPException: 예측 실패 시
        """
        if not self.ml_service:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="ML service not available - dependencies not properly initialized",
            )

        request_id = request_id or str(uuid.uuid4())

        logger.info(
            "predict_prices_request_received",
            request_id=request_id,
            symbol=request.symbol,
            prediction_date=request.prediction_date,
            model_version=request.model_version,
        )

        try:
            # 비즈니스 로직 호출
            result = await self.ml_service.predict_prices(
                symbol=request.symbol,
                prediction_date=request.prediction_date,
                model_version=request.model_version,
                save_results=request.save_results,
            )

            if result["status"] == "success":
                # 예측 결과 변환
                predictions = []
                for pred in result["predictions"]:
                    predictions.append(
                        PredictionResult(
                            timeframe=pred["timeframe"],
                            target_date=(
                                pred["target_date"].isoformat()
                                if isinstance(pred["target_date"], date)
                                else pred["target_date"]
                            ),
                            predicted_price=pred["predicted_price"],
                            current_price=result["current_price"],
                            price_change_percent=pred["price_change_percent"],
                            predicted_direction=pred["predicted_direction"],
                            confidence_score=pred["confidence_score"],
                        )
                    )

                # 모델 정보 변환
                model_info = ModelInfo(
                    model_id=result.get("model_id"),
                    model_name=f"{request.symbol.replace('^', '')}_lstm",
                    model_version=result.get("model_version", "unknown"),
                    model_type=result.get("model_type", "lstm"),
                    symbol=request.symbol,
                    is_active=True,
                    training_date=None,
                    created_at=result.get("created_at", datetime.now().isoformat()),
                )

                return PredictionResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Prediction completed successfully",
                    timestamp=datetime.now().isoformat(),
                    symbol=request.symbol,
                    prediction_date=(
                        result["prediction_date"].isoformat()
                        if isinstance(result["prediction_date"], date)
                        else result["prediction_date"]
                    ),
                    model_info=model_info,
                    predictions=predictions,
                    batch_id=result.get("batch_id"),
                )

            else:
                # 예측 실패
                error_response = create_error_response(
                    error_code=ErrorCode.PREDICTION_FAILED,
                    message=result.get("error", "Prediction failed"),
                    request_id=request_id,
                )

                raise HTTPException(
                    status_code=ERROR_HTTP_STATUS[ErrorCode.PREDICTION_FAILED],
                    detail=error_response.dict(),
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "predict_prices_handler_error",
                request_id=request_id,
                symbol=request.symbol,
                error=str(e),
            )

            error_response = create_error_response(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Prediction failed: {str(e)}",
                request_id=request_id,
            )

            raise HTTPException(
                status_code=ERROR_HTTP_STATUS[ErrorCode.INTERNAL_SERVER_ERROR],
                detail=error_response.dict(),
            )

    async def get_service_status(
        self, request_id: Optional[str] = None
    ) -> ServiceStatusResponse:
        """
        서비스 상태 조회

        Args:
            request_id: 요청 ID

        Returns:
            서비스 상태 응답
        """
        request_id = request_id or str(uuid.uuid4())

        try:
            if self.ml_service and self.model_service:
                # 완전한 서비스 상태
                ml_status = await self.ml_service.get_service_status()
                model_status = self.model_service.get_service_status()

                health_check = {
                    "ml_service": "healthy",
                    "model_service": "healthy",
                    "database": "healthy",
                    "last_check": datetime.now().isoformat(),
                }

                return ServiceStatusResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Service status retrieved successfully",
                    timestamp=datetime.now().isoformat(),
                    service="MLPredictionAPI",
                    version="1.0.0",
                    config={
                        "ml_service": ml_status["config"],
                        "model_service": model_status["config"],
                    },
                    components={
                        "ml_service": ml_status["status"],
                        "model_service": model_status["status"],
                        "trainer": ml_status["components"]["trainer"],
                        "predictor": ml_status["components"]["predictor"],
                        "evaluator": ml_status["components"]["evaluator"],
                    },
                    health_check=health_check,
                )
            else:
                # 폴백 상태
                health_check = {
                    "ml_service": "not_ready",
                    "model_service": "not_ready",
                    "database": "healthy",
                    "last_check": datetime.now().isoformat(),
                    "note": "Service initialization failed",
                }

                return ServiceStatusResponse(
                    status=ResponseStatus.SUCCESS,
                    message="Service status retrieved (fallback mode)",
                    timestamp=datetime.now().isoformat(),
                    service="MLPredictionAPI",
                    version="1.0.0-fallback",
                    config={
                        "status": "fallback_mode",
                        "issue": "Service initialization failed",
                    },
                    components={
                        "ml_service": "not_ready",
                        "model_service": "not_ready",
                        "trainer": "not_ready",
                        "predictor": "not_ready",
                        "evaluator": "not_ready",
                    },
                    health_check=health_check,
                )

        except Exception as e:
            logger.error(
                "get_service_status_handler_error", request_id=request_id, error=str(e)
            )

            error_response = create_error_response(
                error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                message=f"Status retrieval failed: {str(e)}",
                request_id=request_id,
            )

            raise HTTPException(
                status_code=ERROR_HTTP_STATUS[ErrorCode.INTERNAL_SERVER_ERROR],
                detail=error_response.dict(),
            )

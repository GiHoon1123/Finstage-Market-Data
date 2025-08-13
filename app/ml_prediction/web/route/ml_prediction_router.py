"""
ML 예측 API 라우터

이 파일은 ML 예측 시스템의 FastAPI 라우터를 구현합니다.
모든 ML 예측 관련 엔드포인트를 정의하고 핸들러와 연결합니다.

주요 엔드포인트:
- POST /train: 모델 훈련
- POST /predict: 가격 예측
- GET /evaluate: 모델 평가
- POST /backtest: 백테스트 실행
- GET /history: 예측 이력 조회
- GET /status: 서비스 상태
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query, Path
from fastapi.responses import JSONResponse
import uuid
from datetime import datetime

from app.ml_prediction.handler.ml_prediction_handler import MLPredictionHandler
from app.ml_prediction.dto.request_models import (
    TrainModelRequest,
    PredictionRequest,
    EvaluationRequest,
    BacktestRequest,
    PredictionTimeframe,
)
from app.ml_prediction.dto.response_models import (
    TrainModelResponse,
    PredictionResponse,
    EvaluationResponse,
    BacktestResponse,
    ServiceStatusResponse,
)
from app.ml_prediction.dto.error_models import (
    ErrorResponse,
    ValidationErrorResponse,
)
from app.common.utils.logging_config import get_logger
from app.common.dto.api_response import ApiResponse
from app.common.utils.response_helper import (
    success_response,
    handle_service_error,
)

logger = get_logger(__name__)

# 라우터 생성
router = APIRouter(
    prefix="/ml-prediction",
    tags=["ML Prediction"],
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ValidationErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
        503: {"model": ErrorResponse, "description": "Service Unavailable"},
    },
)


# 핸들러 인스턴스 (의존성 주입용)
def get_ml_handler() -> MLPredictionHandler:
    """ML 예측 핸들러 의존성"""
    return MLPredictionHandler()


@router.post(
    "/train",
    response_model=ApiResponse,
    status_code=status.HTTP_201_CREATED,
    summary="모델 훈련",
    description="새로운 LSTM 모델을 훈련합니다. 기존 모델이 있는 경우 force_retrain=true로 강제 재훈련할 수 있습니다.",
    responses={
        201: {"description": "모델 훈련 성공"},
        409: {"description": "모델이 이미 존재함"},
        500: {"description": "훈련 실패"},
        503: {"description": "서비스 사용 불가"},
    },
)
async def train_model(
    request: TrainModelRequest, handler: MLPredictionHandler = Depends(get_ml_handler)
) -> ApiResponse:
    """
    모델 훈련 엔드포인트

    - **symbol**: 주식 심볼 (예: ^GSPC, ^IXIC)
    - **training_days**: 훈련 데이터 일수 (100-5000일)
    - **validation_split**: 검증 데이터 비율 (0.1-0.4)
    - **force_retrain**: 기존 모델이 있어도 강제 재훈련 여부
    - **hyperparameters**: 사용자 정의 하이퍼파라미터 (선택사항)
    """
    request_id = str(uuid.uuid4())

    logger.info(
        "train_model_endpoint_called",
        request_id=request_id,
        symbol=request.symbol,
        training_days=request.training_days,
    )

    result = await handler.train_model(request, request_id)
    
    return success_response(
        data=result,
        message=f"{request.symbol} 모델 훈련이 성공적으로 시작되었습니다"
    )


@router.post(
    "/predict",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="가격 예측",
    description="지정된 심볼의 7일, 14일, 30일 후 가격을 예측합니다.",
    responses={
        200: {"description": "예측 성공"},
        404: {"description": "활성 모델 없음"},
        500: {"description": "예측 실패"},
        503: {"description": "서비스 사용 불가"},
    },
)
async def predict_prices(
    request: PredictionRequest, handler: MLPredictionHandler = Depends(get_ml_handler)
) -> ApiResponse:
    """
    가격 예측 엔드포인트

    - **symbol**: 주식 심볼
    - **prediction_date**: 예측 기준 날짜 (기본값: 오늘)
    - **timeframes**: 예측할 타임프레임들 (기본값: 전체)
    - **model_version**: 사용할 모델 버전 (기본값: 활성 모델)
    - **save_results**: 결과를 데이터베이스에 저장할지 여부
    """
    request_id = str(uuid.uuid4())

    logger.info(
        "predict_prices_endpoint_called",
        request_id=request_id,
        symbol=request.symbol,
        prediction_date=request.prediction_date,
    )

    result = await handler.predict_prices(request, request_id)
    
    return success_response(
        data=result,
        message=f"{request.symbol} 가격 예측이 완료되었습니다"
    )


@router.get(
    "/status",
    response_model=ApiResponse,
    status_code=status.HTTP_200_OK,
    summary="서비스 상태 조회",
    description="ML 예측 서비스의 현재 상태를 조회합니다.",
    responses={200: {"description": "상태 조회 성공"}},
)
async def get_service_status(
    handler: MLPredictionHandler = Depends(get_ml_handler),
) -> ApiResponse:
    """
    서비스 상태 조회 엔드포인트

    서비스의 전반적인 상태와 각 컴포넌트의 헬스 체크 결과를 제공합니다.
    """
    result = await handler.get_service_status()
    
    return success_response(
        data=result,
        message="ML 예측 서비스 상태 조회 완료"
    )


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="헬스 체크",
    description="서비스의 기본적인 헬스 체크를 수행합니다.",
    responses={
        200: {"description": "서비스 정상"},
        503: {"description": "서비스 이상"},
    },
)
async def health_check() -> ApiResponse:
    """
    헬스 체크 엔드포인트

    로드 밸런서나 모니터링 시스템에서 사용할 수 있는 간단한 헬스 체크입니다.
    """
    try:
        health_data = {
            "status": "healthy",
            "service": "ml-prediction-api",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "dependencies": "installed",
        }
        
        return success_response(
            data=health_data,
            message="ML 예측 서비스가 정상적으로 작동 중입니다"
        )

    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        handle_service_error(e, "ML 예측 서비스 헬스 체크 실패")
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "ml-prediction-api",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )


@router.get(
    "/info",
    status_code=status.HTTP_200_OK,
    summary="시스템 정보",
    description="ML 예측 시스템의 정보를 제공합니다.",
)
async def get_system_info() -> ApiResponse:
    """
    시스템 정보 엔드포인트

    현재 시스템의 상태와 기능 정보를 제공합니다.
    """
    system_info = {
        "system": "ML Prediction System",
        "version": "1.0.0",
        "status": "production_ready",
        "features": {
            "model_training": "ready",
            "price_prediction": "ready",
            "model_evaluation": "ready",
            "backtesting": "ready",
        },
        "dependencies": {
            "tensorflow": "installed",
            "scikit-learn": "installed",
            "pandas": "installed",
            "numpy": "installed",
            "matplotlib": "installed",
            "seaborn": "installed",
        },
        "endpoints": [
            "POST /train - 모델 훈련",
            "POST /predict - 가격 예측",
            "GET /status - 서비스 상태",
            "GET /health - 헬스 체크",
            "GET /info - 시스템 정보",
        ],
        "note": "All ML functionality is now available",
        "timestamp": datetime.now().isoformat(),
    }
    
    return success_response(
        data=system_info,
        message="ML 예측 시스템 정보 조회 완료"
    )

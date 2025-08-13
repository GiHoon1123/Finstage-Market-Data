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
    summary="ML 모델 훈련",
    description="""
    새로운 LSTM 모델을 훈련합니다.
    
    **주요 기능:**
    - 지정된 심볼의 과거 데이터를 사용하여 LSTM 모델 훈련
    - 기존 모델이 있는 경우 force_retrain 옵션으로 재훈련 가능
    - 하이퍼파라미터 커스터마이징 지원
    - 훈련 진행 상황 실시간 모니터링
    
    **사용 예시:**
    ```json
    {
      "symbol": "^GSPC",
      "training_days": 1000,
      "validation_split": 0.2,
      "force_retrain": false,
      "hyperparameters": {
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 100
      }
    }
    ```
    """,
    responses={
        201: {
            "description": "모델 훈련 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 201,
                        "message": "^GSPC 모델 훈련이 성공적으로 시작되었습니다",
                        "data": {
                            "status": "success",
                            "message": "Model training completed successfully",
                            "timestamp": "2025-08-13T13:30:00Z",
                            "symbol": "^GSPC",
                            "model_version": "v1.0.0_20250813_133000",
                            "training_metrics": {
                                "final_loss": 0.0023,
                                "final_mae": 0.0156,
                                "training_time_minutes": 25
                            },
                            "model_info": {
                                "model_name": "GSPC_lstm",
                                "model_type": "lstm",
                                "is_active": True,
                                "training_date": "2025-08-13T13:30:00Z"
                            }
                        }
                    }
                }
            },
        },
        409: {
            "description": "모델이 이미 존재함",
            "content": {
                "application/json": {
                    "example": {
                        "status": 409,
                        "message": "모델이 이미 존재합니다",
                        "data": {
                            "status": "skipped",
                            "message": "Model already exists",
                            "existing_model": {
                                "model_version": "v1.0.0_20250813_110520",
                                "is_active": True,
                                "training_date": "2025-08-13T11:05:28Z"
                            }
                        }
                    }
                }
            }
        },
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
    summary="주식 가격 예측",
    description="""
    훈련된 ML 모델을 사용하여 주식 가격을 예측합니다.
    
    **주요 기능:**
    - 7일, 14일, 30일 후 가격 예측
    - 예측 신뢰도 점수 제공
    - 여러 타임프레임 동시 예측
    - 특정 모델 버전 선택 가능
    
    **사용 예시:**
    ```json
    {
      "symbol": "^GSPC",
      "prediction_date": "2025-08-13",
      "timeframes": ["7d", "14d", "30d"],
      "model_version": null,
      "save_results": True
    }
    ```
    
    **주의사항:**
    - model_version이 null이면 현재 활성 모델 사용
    - model_version이 "string"이면 오류 발생 (null 또는 실제 버전명 사용)
    """,
    responses={
        200: {
            "description": "예측 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "^GSPC 가격 예측이 완료되었습니다",
                        "data": {
                            "status": "success",
                            "message": "Prediction completed successfully",
                            "timestamp": "2025-08-13T13:30:00Z",
                            "symbol": "^GSPC",
                            "prediction_date": "2025-08-13",
                            "model_info": {
                                "model_id": 10,
                                "model_name": "GSPC_lstm",
                                "model_version": "v1.0.0_20250813_110520",
                                "model_type": "lstm",
                                "symbol": "^GSPC",
                                "is_active": True,
                                "training_date": "2025-08-13T11:05:28Z"
                            },
                            "predictions": [
                                {
                                    "timeframe": "7d",
                                    "target_date": "2025-08-20",
                                    "predicted_price": 6230.61,
                                    "current_price": 6340.0,
                                    "price_change_percent": -1.73,
                                    "predicted_direction": "down",
                                    "confidence_score": 0.9
                                },
                                {
                                    "timeframe": "14d",
                                    "target_date": "2025-08-27",
                                    "predicted_price": 6269.28,
                                    "current_price": 6340.0,
                                    "price_change_percent": -1.12,
                                    "predicted_direction": "down",
                                    "confidence_score": 0.9
                                },
                                {
                                    "timeframe": "30d",
                                    "target_date": "2025-09-12",
                                    "predicted_price": 6249.46,
                                    "current_price": 6340.0,
                                    "price_change_percent": -1.43,
                                    "predicted_direction": "down",
                                    "confidence_score": 0.9
                                }
                            ],
                            "batch_id": "68aaa6bd-7395-4079-b69b-058ee4910fbf"
                        }
                    }
                }
            },
        },
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
    responses={
        200: {
            "description": "상태 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "ML 예측 서비스 상태 조회 완료",
                        "data": {
                            "service_status": "healthy",
                            "active_models": ["^GSPC", "^IXIC"],
                            "model_versions": {
                                "^GSPC": "v1.0.0",
                                "^IXIC": "v1.0.0"
                            },
                            "last_training": "2025-08-13T10:00:00Z",
                            "total_predictions": 1250,
                            "average_accuracy": 0.78
                        }
                    }
                }
            },
        }
    },
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
        200: {
            "description": "서비스 정상",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "ML 예측 서비스가 정상적으로 작동 중입니다",
                        "data": {
                            "status": "healthy",
                            "service": "ml-prediction-api",
                            "timestamp": "2025-08-13T13:30:00Z",
                            "version": "1.0.0",
                            "dependencies": "installed"
                        }
                    }
                }
            },
        },
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


@router.get(
    "/info",
    status_code=status.HTTP_200_OK,
    summary="시스템 정보",
    description="ML 예측 시스템의 정보를 제공합니다.",
    responses={
        200: {
            "description": "시스템 정보 조회 성공",
            "content": {
                "application/json": {
                    "example": {
                        "status": 200,
                        "message": "ML 예측 시스템 정보 조회 완료",
                        "data": {
                            "system": "ML Prediction System",
                            "version": "1.0.0",
                            "status": "production_ready",
                            "features": {
                                "model_training": "ready",
                                "price_prediction": "ready",
                                "model_evaluation": "ready",
                                "backtesting": "ready"
                            },
                            "dependencies": {
                                "tensorflow": "installed",
                                "scikit-learn": "installed",
                                "pandas": "installed",
                                "numpy": "installed"
                            },
                            "endpoints": [
                                "POST /train - 모델 훈련",
                                "POST /predict - 가격 예측",
                                "GET /status - 서비스 상태",
                                "GET /health - 헬스 체크"
                            ],
                            "note": "All ML functionality is now available",
                            "timestamp": "2025-08-13T13:30:00Z"
                        }
                    }
                }
            },
        }
    },
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

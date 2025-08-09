"""
ML 예측 API 요청 모델

이 파일은 ML 예측 API의 요청 데이터 모델들을 정의합니다.
Pydantic을 사용하여 입력 검증 및 직렬화를 처리합니다.

주요 모델:
- 모델 훈련 요청
- 예측 요청
- 평가 요청
- 백테스트 요청
"""

from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class PredictionTimeframe(str, Enum):
    """예측 타임프레임"""

    SEVEN_DAYS = "7d"
    FOURTEEN_DAYS = "14d"
    THIRTY_DAYS = "30d"


class ModelType(str, Enum):
    """모델 타입"""

    LSTM = "lstm"


class TradingStrategy(str, Enum):
    """거래 전략"""

    DIRECTION_BASED = "direction_based"
    MOMENTUM_BASED = "momentum_based"


class TrainModelRequest(BaseModel):
    """모델 훈련 요청"""

    symbol: str = Field(
        ..., description="주식 심볼 (예: ^GSPC, ^IXIC)", example="^GSPC"
    )

    training_days: int = Field(
        default=1000, ge=100, le=5000, description="훈련 데이터 일수 (100-5000일)"
    )

    validation_split: float = Field(
        default=0.2, ge=0.1, le=0.4, description="검증 데이터 비율 (0.1-0.4)"
    )

    force_retrain: bool = Field(
        default=False, description="기존 모델이 있어도 강제로 재훈련할지 여부"
    )

    hyperparameters: Optional[Dict[str, Any]] = Field(
        default=None, description="사용자 정의 하이퍼파라미터"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()


class PredictionRequest(BaseModel):
    """예측 요청"""

    symbol: str = Field(..., description="주식 심볼", example="^GSPC")

    prediction_date: Optional[date] = Field(
        default=None, description="예측 기준 날짜 (기본값: 오늘)"
    )

    timeframes: Optional[List[PredictionTimeframe]] = Field(
        default=None, description="예측할 타임프레임들 (기본값: 전체)"
    )

    model_version: Optional[str] = Field(
        default=None, description="사용할 모델 버전 (기본값: 활성 모델)"
    )

    save_results: bool = Field(
        default=True, description="예측 결과를 데이터베이스에 저장할지 여부"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    @validator("prediction_date")
    def validate_prediction_date(cls, v):
        if v and v > date.today():
            raise ValueError("Prediction date cannot be in the future")
        return v


class EvaluationRequest(BaseModel):
    """모델 평가 요청"""

    symbol: str = Field(..., description="주식 심볼", example="^GSPC")

    model_version: Optional[str] = Field(
        default=None, description="평가할 모델 버전 (기본값: 활성 모델)"
    )

    evaluation_days: int = Field(
        default=90, ge=7, le=365, description="평가 기간 (7-365일)"
    )

    include_visualizations: bool = Field(
        default=False, description="시각화 차트 포함 여부"
    )

    timeframes: Optional[List[PredictionTimeframe]] = Field(
        default=None, description="평가할 타임프레임들 (기본값: 전체)"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()


class BacktestRequest(BaseModel):
    """백테스트 요청"""

    symbol: str = Field(..., description="주식 심볼", example="^GSPC")

    model_version: str = Field(..., description="백테스트할 모델 버전")

    start_date: date = Field(..., description="백테스트 시작 날짜")

    end_date: date = Field(..., description="백테스트 종료 날짜")

    strategy: TradingStrategy = Field(
        default=TradingStrategy.DIRECTION_BASED, description="거래 전략"
    )

    initial_capital: float = Field(
        default=100000.0,
        ge=1000.0,
        le=10000000.0,
        description="초기 자본 (1,000 - 10,000,000)",
    )

    position_size: float = Field(
        default=0.1, ge=0.01, le=1.0, description="포지션 크기 비율 (0.01-1.0)"
    )

    transaction_cost: float = Field(
        default=0.001, ge=0.0, le=0.01, description="거래 비용 비율 (0.0-0.01)"
    )

    confidence_threshold: float = Field(
        default=0.6, ge=0.5, le=1.0, description="거래 실행 최소 신뢰도 (0.5-1.0)"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    @validator("end_date")
    def validate_date_range(cls, v, values):
        if "start_date" in values and v <= values["start_date"]:
            raise ValueError("End date must be after start date")
        if v > date.today():
            raise ValueError("End date cannot be in the future")
        return v


class ModelComparisonRequest(BaseModel):
    """모델 비교 요청"""

    symbol: str = Field(..., description="주식 심볼", example="^GSPC")

    model_versions: List[str] = Field(
        ..., min_items=2, max_items=5, description="비교할 모델 버전들 (2-5개)"
    )

    evaluation_days: int = Field(
        default=90, ge=7, le=365, description="평가 기간 (7-365일)"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()


class PredictionHistoryRequest(BaseModel):
    """예측 이력 조회 요청"""

    symbol: str = Field(..., description="주식 심볼", example="^GSPC")

    start_date: Optional[date] = Field(
        default=None, description="조회 시작 날짜 (기본값: 30일 전)"
    )

    end_date: Optional[date] = Field(
        default=None, description="조회 종료 날짜 (기본값: 오늘)"
    )

    timeframe: Optional[PredictionTimeframe] = Field(
        default=None, description="타임프레임 필터"
    )

    include_actual_results: bool = Field(
        default=True, description="실제 결과가 있는 예측만 포함할지 여부"
    )

    limit: int = Field(
        default=100, ge=1, le=1000, description="최대 조회 개수 (1-1000)"
    )

    @validator("symbol")
    def validate_symbol(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol cannot be empty")
        return v.strip().upper()

    @validator("end_date")
    def validate_date_range(cls, v, values):
        if (
            v
            and "start_date" in values
            and values["start_date"]
            and v <= values["start_date"]
        ):
            raise ValueError("End date must be after start date")
        return v


class ModelManagementRequest(BaseModel):
    """모델 관리 요청"""

    action: str = Field(..., description="수행할 액션 (activate, deactivate, delete)")

    model_name: str = Field(..., description="모델 이름")

    model_version: str = Field(..., description="모델 버전")

    delete_files: bool = Field(
        default=True, description="삭제 시 모델 파일도 함께 삭제할지 여부"
    )

    @validator("action")
    def validate_action(cls, v):
        allowed_actions = ["activate", "deactivate", "delete"]
        if v not in allowed_actions:
            raise ValueError(f"Action must be one of: {allowed_actions}")
        return v


class UpdatePredictionResultsRequest(BaseModel):
    """예측 결과 업데이트 요청"""

    target_date: Optional[date] = Field(
        default=None, description="업데이트할 날짜 (기본값: 어제)"
    )

    symbols: Optional[List[str]] = Field(
        default=None, description="특정 심볼들만 업데이트 (기본값: 전체)"
    )

    days_back: int = Field(
        default=1, ge=1, le=30, description="며칠 전까지 업데이트할지 (1-30일)"
    )

    @validator("symbols")
    def validate_symbols(cls, v):
        if v:
            return [symbol.strip().upper() for symbol in v if symbol.strip()]
        return v


class BatchPredictionRequest(BaseModel):
    """배치 예측 요청"""

    symbols: List[str] = Field(
        ..., min_items=1, max_items=50, description="예측할 심볼들 (1-50개)"
    )

    prediction_date: Optional[date] = Field(
        default=None, description="예측 기준 날짜 (기본값: 오늘)"
    )

    timeframes: Optional[List[PredictionTimeframe]] = Field(
        default=None, description="예측할 타임프레임들 (기본값: 전체)"
    )

    save_results: bool = Field(
        default=True, description="예측 결과를 데이터베이스에 저장할지 여부"
    )

    @validator("symbols")
    def validate_symbols(cls, v):
        if not v:
            raise ValueError("At least one symbol is required")
        return [symbol.strip().upper() for symbol in v if symbol.strip()]

    @validator("prediction_date")
    def validate_prediction_date(cls, v):
        if v and v > date.today():
            raise ValueError("Prediction date cannot be in the future")
        return v

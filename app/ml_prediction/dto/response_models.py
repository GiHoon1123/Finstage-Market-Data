"""
ML 예측 API 응답 모델

이 파일은 ML 예측 API의 응답 데이터 모델들을 정의합니다.
Pydantic을 사용하여 출력 직렬화 및 API 문서화를 처리합니다.

주요 모델:
- 모델 훈련 응답
- 예측 응답
- 평가 응답
- 백테스트 응답
"""

from typing import Optional, List, Dict, Any, Union
from datetime import date, datetime
from pydantic import BaseModel, Field
from enum import Enum


class ResponseStatus(str, Enum):
    """응답 상태"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class PredictionDirection(str, Enum):
    """예측 방향"""

    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class PerformanceGrade(str, Enum):
    """성능 등급"""

    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    INSUFFICIENT_DATA = "insufficient_data"


class BaseResponse(BaseModel):
    """기본 응답 모델"""

    status: ResponseStatus = Field(..., description="응답 상태")

    message: Optional[str] = Field(default=None, description="응답 메시지")

    timestamp: str = Field(..., description="응답 생성 시간 (ISO 형식)")


class ErrorResponse(BaseResponse):
    """에러 응답 모델"""

    error: str = Field(..., description="에러 메시지")

    error_code: Optional[str] = Field(default=None, description="에러 코드")

    details: Optional[Dict[str, Any]] = Field(
        default=None, description="에러 상세 정보"
    )


class ModelInfo(BaseModel):
    """모델 정보"""

    model_id: Optional[int] = Field(default=None, description="모델 ID")

    model_name: str = Field(..., description="모델 이름")

    model_version: str = Field(..., description="모델 버전")

    model_type: str = Field(..., description="모델 타입")

    symbol: str = Field(..., description="심볼")

    is_active: bool = Field(..., description="활성 모델 여부")

    training_date: Optional[str] = Field(default=None, description="훈련 완료 날짜")

    created_at: str = Field(..., description="생성 시간")


class TrainingMetrics(BaseModel):
    """훈련 지표"""

    loss: float = Field(..., description="최종 손실값")

    val_loss: float = Field(..., description="검증 손실값")

    epochs_trained: int = Field(..., description="훈련된 에포크 수")

    training_time_seconds: float = Field(..., description="훈련 소요 시간 (초)")


class TrainModelResponse(BaseResponse):
    """모델 훈련 응답"""

    model_info: Optional[ModelInfo] = Field(
        default=None, description="훈련된 모델 정보"
    )

    training_metrics: Optional[TrainingMetrics] = Field(
        default=None, description="훈련 지표"
    )

    initial_evaluation: Optional[Dict[str, Any]] = Field(
        default=None, description="초기 성능 평가 결과"
    )

    existing_model: Optional[ModelInfo] = Field(
        default=None, description="기존 모델 정보 (스킵된 경우)"
    )


class PredictionResult(BaseModel):
    """개별 예측 결과"""

    timeframe: str = Field(..., description="예측 타임프레임", example="7d")

    target_date: str = Field(..., description="예측 대상 날짜 (ISO 형식)")

    predicted_price: float = Field(..., description="예측 가격 (지수는 포인트, 주식은 달러)")

    current_price: float = Field(..., description="현재 가격 (지수는 포인트, 주식은 달러)")

    price_change_percent: float = Field(..., description="예상 가격 변화율 (%)")

    predicted_direction: PredictionDirection = Field(..., description="예측 방향")

    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="신뢰도 점수 (0-1)"
    )


class PredictionResponse(BaseResponse):
    """예측 응답"""

    symbol: str = Field(..., description="심볼")

    prediction_date: str = Field(..., description="예측 기준 날짜")

    model_info: ModelInfo = Field(..., description="사용된 모델 정보")

    predictions: List[PredictionResult] = Field(..., description="예측 결과들")

    batch_id: Optional[str] = Field(default=None, description="배치 ID (저장된 경우)")


class TimeframePerformance(BaseModel):
    """타임프레임별 성능"""

    mse: float = Field(..., description="평균 제곱 오차")

    mae: float = Field(..., description="평균 절대 오차")

    rmse: float = Field(..., description="평균 제곱근 오차")

    r2_score: float = Field(..., description="R² 점수")

    direction_accuracy: float = Field(
        ..., ge=0.0, le=1.0, description="방향 정확도 (0-1)"
    )

    mape: float = Field(..., description="평균 절대 백분율 오차")

    prediction_count: int = Field(..., description="예측 개수")


class OverallPerformance(BaseModel):
    """전체 성능"""

    avg_direction_accuracy: float = Field(..., description="평균 방향 정확도")

    avg_mse: float = Field(..., description="평균 MSE")

    avg_mae: float = Field(..., description="평균 MAE")

    total_predictions: int = Field(..., description="총 예측 개수")


class PerformanceAssessment(BaseModel):
    """성능 평가"""

    grade: PerformanceGrade = Field(..., description="성능 등급")

    meets_threshold: bool = Field(..., description="성능 임계값 충족 여부")

    threshold_comparison: Dict[str, Dict[str, Union[float, bool]]] = Field(
        ..., description="임계값 비교 결과"
    )


class EvaluationResponse(BaseResponse):
    """모델 평가 응답"""

    symbol: str = Field(..., description="심볼")

    model_info: ModelInfo = Field(..., description="평가된 모델 정보")

    evaluation_period: Dict[str, Union[str, int]] = Field(
        ..., description="평가 기간 정보"
    )

    timeframe_performance: Dict[str, TimeframePerformance] = Field(
        ..., description="타임프레임별 성능"
    )

    overall_performance: OverallPerformance = Field(..., description="전체 성능")

    performance_assessment: Optional[PerformanceAssessment] = Field(
        default=None, description="성능 평가"
    )

    visualizations: Optional[Dict[str, str]] = Field(
        default=None, description="시각화 차트들 (Base64 인코딩)"
    )


class TradeResult(BaseModel):
    """거래 결과"""

    entry_date: str = Field(..., description="진입 날짜")

    exit_date: Optional[str] = Field(default=None, description="청산 날짜")

    entry_price: float = Field(..., description="진입 가격")

    exit_price: Optional[float] = Field(default=None, description="청산 가격")

    direction: str = Field(..., description="거래 방향 (long/short)")

    timeframe: str = Field(..., description="예측 타임프레임")

    pnl: Optional[float] = Field(default=None, description="손익")

    return_pct: Optional[float] = Field(default=None, description="수익률 (%)")

    is_closed: bool = Field(..., description="거래 완료 여부")


class BacktestResponse(BaseResponse):
    """백테스트 응답"""

    symbol: str = Field(..., description="심볼")

    model_version: str = Field(..., description="모델 버전")

    strategy: str = Field(..., description="거래 전략")

    period: Dict[str, Union[str, int]] = Field(..., description="백테스트 기간")

    config: Dict[str, Union[float, int]] = Field(..., description="백테스트 설정")

    trades: Dict[str, Union[int, List[TradeResult]]] = Field(
        ..., description="거래 정보"
    )

    performance_metrics: Dict[str, float] = Field(..., description="성과 지표")

    risk_metrics: Dict[str, float] = Field(..., description="리스크 지표")

    benchmark_comparison: Dict[str, Union[float, bool]] = Field(
        ..., description="벤치마크 비교"
    )


class PredictionHistoryItem(BaseModel):
    """예측 이력 항목"""

    id: int = Field(..., description="예측 ID")

    prediction_date: str = Field(..., description="예측 날짜")

    target_date: str = Field(..., description="대상 날짜")

    timeframe: str = Field(..., description="타임프레임")

    predicted_price: float = Field(..., description="예측 가격")

    actual_price: Optional[float] = Field(default=None, description="실제 가격")

    predicted_direction: PredictionDirection = Field(..., description="예측 방향")

    is_direction_correct: Optional[bool] = Field(
        default=None, description="방향 예측 정확 여부"
    )

    confidence_score: float = Field(..., description="신뢰도 점수")

    price_error_percent: Optional[float] = Field(
        default=None, description="가격 오차율 (%)"
    )

    model_version: str = Field(..., description="모델 버전")


class PredictionHistoryResponse(BaseResponse):
    """예측 이력 응답"""

    symbol: str = Field(..., description="심볼")

    period: Dict[str, str] = Field(..., description="조회 기간")

    filter: Dict[str, Union[str, bool]] = Field(..., description="적용된 필터")

    statistics: Dict[str, Union[int, float]] = Field(..., description="통계 정보")

    predictions: List[PredictionHistoryItem] = Field(..., description="예측 이력")


class ModelComparisonResponse(BaseResponse):
    """모델 비교 응답"""

    symbol: str = Field(..., description="심볼")

    model_versions: List[str] = Field(..., description="비교된 모델 버전들")

    performance_comparison: Dict[str, Dict[str, float]] = Field(
        ..., description="성능 비교 결과"
    )

    best_model: str = Field(..., description="최고 성능 모델")

    improvement_percentage: float = Field(..., description="개선 정도 (%)")


class ModelListResponse(BaseResponse):
    """모델 목록 응답"""

    models: List[ModelInfo] = Field(..., description="모델 목록")

    total_count: int = Field(..., description="총 모델 개수")

    filter: Dict[str, Union[str, bool]] = Field(..., description="적용된 필터")


class ServiceStatusResponse(BaseResponse):
    """서비스 상태 응답"""

    service: str = Field(..., description="서비스 이름")

    version: Optional[str] = Field(default=None, description="서비스 버전")

    config: Dict[str, Any] = Field(..., description="서비스 설정")

    components: Dict[str, str] = Field(..., description="컴포넌트 상태")

    health_check: Dict[str, Union[str, bool, int]] = Field(
        ..., description="헬스 체크 결과"
    )


class BatchPredictionResponse(BaseResponse):
    """배치 예측 응답"""

    prediction_date: str = Field(..., description="예측 기준 날짜")

    total_symbols: int = Field(..., description="총 심볼 개수")

    successful_predictions: int = Field(..., description="성공한 예측 개수")

    failed_predictions: int = Field(..., description="실패한 예측 개수")

    results: List[Dict[str, Union[str, List[PredictionResult], str]]] = Field(
        ..., description="심볼별 예측 결과"
    )

    batch_id: Optional[str] = Field(default=None, description="배치 ID")


class UpdateResultsResponse(BaseResponse):
    """예측 결과 업데이트 응답"""

    target_date: str = Field(..., description="업데이트 대상 날짜")

    total_predictions: int = Field(..., description="총 예측 개수")

    updated_predictions: int = Field(..., description="업데이트된 예측 개수")

    failed_updates: int = Field(..., description="실패한 업데이트 개수")

    symbols_processed: List[str] = Field(..., description="처리된 심볼들")

    update_results: List[Dict[str, Union[str, int]]] = Field(
        ..., description="심볼별 업데이트 결과"
    )

"""
ML 예측 결과 엔티티

이 파일은 딥러닝 모델의 예측 결과를 저장하기 위한 엔티티입니다.
멀티 타임프레임 예측 (7일, 14일, 30일)을 지원하며, 예측 정확도 추적을 위해
실제 결과와 비교할 수 있는 구조로 설계되었습니다.

주요 기능:
- 멀티 타임프레임 예측 결과 저장
- 예측 신뢰도 및 방향성 저장
- 실제 결과와의 비교를 위한 업데이트 지원
- 동시 예측 배치 그룹핑 (batch_id)
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    Date,
    DateTime,
    Boolean,
    Text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.common.infra.database.config.database_config import Base
from typing import Dict, Any, Optional
import json
from datetime import date, datetime


class MLPrediction(Base):
    """
    ML 예측 결과 테이블

    딥러닝 모델의 멀티 타임프레임 예측 결과를 저장합니다.
    각 예측은 7일, 14일, 30일 중 하나의 기간에 대한 결과이며,
    동일한 요청에서 생성된 예측들은 batch_id로 그룹핑됩니다.
    """

    __tablename__ = "ml_predictions"

    # =================================================================
    # 기본 식별 정보
    # =================================================================

    id = Column(
        BigInteger, primary_key=True, autoincrement=True, comment="ML 예측 결과 고유 ID"
    )

    symbol = Column(
        String(10), nullable=False, comment="심볼 (^IXIC: 나스닥, ^GSPC: S&P 500)"
    )

    prediction_date = Column(Date, nullable=False, comment="예측을 수행한 날짜")

    prediction_timeframe = Column(
        String(10), nullable=False, comment="예측 기간 (7d, 14d, 30d)"
    )

    target_date = Column(
        Date, nullable=False, comment="예측 대상 날짜 (prediction_date + timeframe)"
    )

    batch_id = Column(
        String(50),
        nullable=False,
        comment="동시 예측 배치 ID (같은 요청의 7d/14d/30d 연결)",
    )

    # =================================================================
    # 예측 결과 데이터
    # =================================================================

    current_price = Column(
        DECIMAL(12, 4), nullable=False, comment="예측 시점의 현재 가격"
    )

    predicted_price = Column(DECIMAL(12, 4), nullable=False, comment="예측된 미래 가격")

    predicted_direction = Column(
        String(10), nullable=False, comment="예측 방향 (up, down, neutral)"
    )

    price_change_percent = Column(
        DECIMAL(8, 4), nullable=True, comment="예상 가격 변화율 (%)"
    )

    confidence_score = Column(
        DECIMAL(5, 4), nullable=False, comment="예측 신뢰도 점수 (0.0 ~ 1.0)"
    )

    # =================================================================
    # 실제 결과 (나중에 업데이트)
    # =================================================================

    actual_price = Column(
        DECIMAL(12, 4), nullable=True, comment="실제 가격 (target_date에 업데이트)"
    )

    actual_direction = Column(
        String(10), nullable=True, comment="실제 방향 (up, down, neutral)"
    )

    actual_change_percent = Column(
        DECIMAL(8, 4), nullable=True, comment="실제 가격 변화율 (%)"
    )

    is_direction_correct = Column(Boolean, nullable=True, comment="방향 예측 정확 여부")

    price_error_percent = Column(
        DECIMAL(8, 4), nullable=True, comment="가격 예측 오차율 (%)"
    )

    # =================================================================
    # 모델 및 특성 정보
    # =================================================================

    model_version = Column(String(50), nullable=False, comment="사용된 모델 버전")

    model_type = Column(
        String(20),
        nullable=False,
        default="lstm",
        comment="모델 타입 (lstm, gru, transformer)",
    )

    features_used = Column(Text, nullable=True, comment="사용된 특성 정보 (JSON 형태)")

    feature_count = Column(BigInteger, nullable=True, comment="사용된 특성 개수")

    # =================================================================
    # 메타데이터
    # =================================================================

    created_at = Column(DateTime, default=func.now(), comment="레코드 생성 시점")

    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="레코드 수정 시점"
    )

    result_updated_at = Column(
        DateTime, nullable=True, comment="실제 결과 업데이트 시점"
    )

    # =================================================================
    # 제약조건 및 인덱스
    # =================================================================

    __table_args__ = (
        # 중복 방지: 같은 심볼, 날짜, 기간의 예측은 1개만 허용
        UniqueConstraint(
            "symbol",
            "prediction_date",
            "prediction_timeframe",
            name="uq_symbol_date_timeframe",
        ),
        # 심볼별 조회 최적화
        Index("idx_ml_prediction_symbol", "symbol"),
        # 날짜별 조회 최적화
        Index("idx_ml_prediction_date", "prediction_date"),
        # 타겟 날짜별 조회 최적화 (실제 결과 업데이트용)
        Index("idx_ml_prediction_target_date", "target_date"),
        # 배치별 조회 최적화
        Index("idx_ml_prediction_batch", "batch_id"),
        # 모델 버전별 조회 최적화
        Index("idx_ml_prediction_model", "model_version"),
        # 성능 분석용 복합 인덱스
        Index(
            "idx_ml_prediction_analysis",
            "symbol",
            "prediction_timeframe",
            "prediction_date",
        ),
        # 실제 결과 업데이트 대상 조회용
        Index("idx_ml_prediction_pending_update", "target_date", "actual_price"),
    )

    def __repr__(self):
        return (
            f"<MLPrediction("
            f"symbol={self.symbol}, "
            f"timeframe={self.prediction_timeframe}, "
            f"predicted_price={self.predicted_price}, "
            f"confidence={self.confidence_score}"
            f")>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        엔티티를 딕셔너리로 변환 (API 응답용)
        """
        return {
            "id": self.id,
            "symbol": self.symbol,
            "prediction_date": (
                self.prediction_date.isoformat() if self.prediction_date else None
            ),
            "prediction_timeframe": self.prediction_timeframe,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "batch_id": self.batch_id,
            "prediction": {
                "current_price": (
                    float(self.current_price) if self.current_price else None
                ),
                "predicted_price": (
                    float(self.predicted_price) if self.predicted_price else None
                ),
                "predicted_direction": self.predicted_direction,
                "price_change_percent": (
                    float(self.price_change_percent)
                    if self.price_change_percent
                    else None
                ),
                "confidence_score": (
                    float(self.confidence_score) if self.confidence_score else None
                ),
            },
            "actual": {
                "actual_price": float(self.actual_price) if self.actual_price else None,
                "actual_direction": self.actual_direction,
                "actual_change_percent": (
                    float(self.actual_change_percent)
                    if self.actual_change_percent
                    else None
                ),
                "is_direction_correct": self.is_direction_correct,
                "price_error_percent": (
                    float(self.price_error_percent)
                    if self.price_error_percent
                    else None
                ),
            },
            "model": {
                "model_version": self.model_version,
                "model_type": self.model_type,
                "feature_count": self.feature_count,
                "features_used": self.get_features_list(),
            },
            "timestamps": {
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "result_updated_at": (
                    self.result_updated_at.isoformat()
                    if self.result_updated_at
                    else None
                ),
            },
        }

    def get_features_list(self) -> Optional[list]:
        """
        사용된 특성 목록을 파싱하여 반환
        """
        if not self.features_used:
            return None

        try:
            return json.loads(self.features_used)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_features_list(self, features: list) -> None:
        """
        특성 목록을 JSON 문자열로 저장
        """
        if features:
            self.features_used = json.dumps(features)
            self.feature_count = len(features)
        else:
            self.features_used = None
            self.feature_count = 0

    def calculate_price_change_percent(self) -> float:
        """
        예상 가격 변화율 계산
        """
        if not self.current_price or not self.predicted_price:
            return 0.0

        return (
            (float(self.predicted_price) - float(self.current_price))
            / float(self.current_price)
        ) * 100

    def update_actual_result(self, actual_price: float) -> None:
        """
        실제 결과로 예측 정확도 업데이트

        Args:
            actual_price: 실제 가격
        """
        self.actual_price = actual_price
        self.result_updated_at = func.now()

        # 실제 변화율 계산
        if self.current_price:
            self.actual_change_percent = (
                (actual_price - float(self.current_price)) / float(self.current_price)
            ) * 100

        # 실제 방향 결정
        if self.actual_change_percent > 0.5:
            self.actual_direction = "up"
        elif self.actual_change_percent < -0.5:
            self.actual_direction = "down"
        else:
            self.actual_direction = "neutral"

        # 방향 예측 정확도
        self.is_direction_correct = self.predicted_direction == self.actual_direction

        # 가격 예측 오차율
        if self.predicted_price:
            self.price_error_percent = (
                abs((actual_price - float(self.predicted_price)) / actual_price) * 100
            )

    def is_prediction_accurate(self, price_tolerance_percent: float = 5.0) -> bool:
        """
        예측이 정확한지 판단

        Args:
            price_tolerance_percent: 가격 허용 오차율 (%)

        Returns:
            방향과 가격 모두 정확한지 여부
        """
        if not self.actual_price:
            return False

        direction_correct = self.is_direction_correct
        price_accurate = (
            self.price_error_percent is not None
            and self.price_error_percent <= price_tolerance_percent
        )

        return direction_correct and price_accurate

    def get_prediction_quality_score(self) -> float:
        """
        예측 품질 점수 계산 (0.0 ~ 1.0)

        방향 정확도와 가격 정확도를 종합하여 점수 산출
        """
        if not self.actual_price:
            return 0.0

        # 방향 점수 (50%)
        direction_score = 0.5 if self.is_direction_correct else 0.0

        # 가격 점수 (50%)
        if self.price_error_percent is not None:
            # 오차율이 낮을수록 높은 점수 (최대 10% 오차 기준)
            price_score = max(
                0.0, 0.5 * (1 - min(self.price_error_percent / 10.0, 1.0))
            )
        else:
            price_score = 0.0

        return direction_score + price_score

    @classmethod
    def create_prediction(
        cls,
        symbol: str,
        prediction_date: date,
        timeframe: str,
        target_date: date,
        batch_id: str,
        current_price: float,
        predicted_price: float,
        confidence_score: float,
        model_version: str,
        model_type: str = "lstm",
        features_used: Optional[list] = None,
    ) -> "MLPrediction":
        """
        새로운 예측 결과 생성

        Args:
            symbol: 심볼
            prediction_date: 예측 날짜
            timeframe: 예측 기간
            target_date: 대상 날짜
            batch_id: 배치 ID
            current_price: 현재 가격
            predicted_price: 예측 가격
            confidence_score: 신뢰도
            model_version: 모델 버전
            model_type: 모델 타입
            features_used: 사용된 특성 목록

        Returns:
            생성된 MLPrediction 인스턴스
        """
        prediction = cls(
            symbol=symbol,
            prediction_date=prediction_date,
            prediction_timeframe=timeframe,
            target_date=target_date,
            batch_id=batch_id,
            current_price=current_price,
            predicted_price=predicted_price,
            confidence_score=confidence_score,
            model_version=model_version,
            model_type=model_type,
        )

        # 예상 변화율 계산
        prediction.price_change_percent = prediction.calculate_price_change_percent()

        # 예측 방향 결정
        if prediction.price_change_percent > 0.5:
            prediction.predicted_direction = "up"
        elif prediction.price_change_percent < -0.5:
            prediction.predicted_direction = "down"
        else:
            prediction.predicted_direction = "neutral"

        # 특성 정보 설정
        if features_used:
            prediction.set_features_list(features_used)

        return prediction

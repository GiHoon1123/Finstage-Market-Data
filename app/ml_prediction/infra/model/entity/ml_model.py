"""
ML 모델 메타데이터 엔티티

이 파일은 훈련된 딥러닝 모델의 메타데이터를 저장하기 위한 엔티티입니다.
모델 버전 관리, 성능 지표, 하이퍼파라미터 등을 추적하여
모델의 생명주기를 완전히 관리할 수 있도록 설계되었습니다.

주요 기능:
- 모델 버전 관리 및 활성 모델 선택
- 훈련 성능 지표 저장
- 하이퍼파라미터 및 설정 정보 저장
- 모델 파일 경로 및 메타데이터 관리
"""

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DECIMAL,
    DateTime,
    Boolean,
    Text,
    Integer,
    Index,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from app.common.infra.database.config.database_config import Base
from typing import Dict, Any, Optional, List
import json
from datetime import datetime


class MLModel(Base):
    """
    ML 모델 메타데이터 테이블

    훈련된 딥러닝 모델의 모든 메타데이터를 저장합니다.
    모델 버전 관리, 성능 추적, 배포 상태 관리를 지원합니다.
    """

    __tablename__ = "ml_models"

    # =================================================================
    # 기본 식별 정보
    # =================================================================

    id = Column(
        BigInteger, primary_key=True, autoincrement=True, comment="ML 모델 고유 ID"
    )

    model_name = Column(
        String(100), nullable=False, comment="모델 이름 (예: nasdaq_lstm_v1)"
    )

    model_version = Column(String(50), nullable=False, comment="모델 버전 (예: v1.0.0)")

    model_type = Column(
        String(20), nullable=False, comment="모델 타입 (lstm, gru, transformer)"
    )

    symbol = Column(String(10), nullable=False, comment="대상 심볼 (^IXIC, ^GSPC)")

    # =================================================================
    # 모델 파일 정보
    # =================================================================

    model_path = Column(String(500), nullable=False, comment="모델 파일 저장 경로")

    model_format = Column(
        String(20),
        nullable=False,
        default="keras",
        comment="모델 파일 형식 (keras, tensorflow, onnx)",
    )

    model_size_mb = Column(DECIMAL(10, 2), nullable=True, comment="모델 파일 크기 (MB)")

    checksum = Column(
        String(64), nullable=True, comment="모델 파일 체크섬 (무결성 검증용)"
    )

    # =================================================================
    # 훈련 정보
    # =================================================================

    training_start_date = Column(DateTime, nullable=False, comment="훈련 시작 시점")

    training_end_date = Column(DateTime, nullable=False, comment="훈련 완료 시점")

    training_duration_minutes = Column(
        Integer, nullable=True, comment="훈련 소요 시간 (분)"
    )

    epochs_trained = Column(Integer, nullable=False, comment="실제 훈련된 에포크 수")

    early_stopped = Column(
        Boolean, nullable=False, default=False, comment="조기 종료 여부"
    )

    # =================================================================
    # 데이터 정보
    # =================================================================

    training_data_start_date = Column(
        DateTime, nullable=False, comment="훈련 데이터 시작 날짜"
    )

    training_data_end_date = Column(
        DateTime, nullable=False, comment="훈련 데이터 종료 날짜"
    )

    training_samples = Column(BigInteger, nullable=False, comment="훈련 샘플 수")

    validation_samples = Column(BigInteger, nullable=False, comment="검증 샘플 수")

    test_samples = Column(BigInteger, nullable=False, comment="테스트 샘플 수")

    feature_count = Column(Integer, nullable=False, comment="사용된 특성 개수")

    window_size = Column(Integer, nullable=False, comment="시계열 윈도우 크기")

    # =================================================================
    # 성능 지표 (7일, 14일, 30일 각각)
    # =================================================================

    # 7일 예측 성능
    performance_7d_mse = Column(
        DECIMAL(12, 8), nullable=True, comment="7일 예측 MSE (Mean Squared Error)"
    )

    performance_7d_mae = Column(
        DECIMAL(12, 8), nullable=True, comment="7일 예측 MAE (Mean Absolute Error)"
    )

    performance_7d_direction_accuracy = Column(
        DECIMAL(5, 4), nullable=True, comment="7일 예측 방향 정확도 (0.0 ~ 1.0)"
    )

    # 14일 예측 성능
    performance_14d_mse = Column(DECIMAL(12, 8), nullable=True, comment="14일 예측 MSE")

    performance_14d_mae = Column(DECIMAL(12, 8), nullable=True, comment="14일 예측 MAE")

    performance_14d_direction_accuracy = Column(
        DECIMAL(5, 4), nullable=True, comment="14일 예측 방향 정확도"
    )

    # 30일 예측 성능
    performance_30d_mse = Column(DECIMAL(12, 8), nullable=True, comment="30일 예측 MSE")

    performance_30d_mae = Column(DECIMAL(12, 8), nullable=True, comment="30일 예측 MAE")

    performance_30d_direction_accuracy = Column(
        DECIMAL(5, 4), nullable=True, comment="30일 예측 방향 정확도"
    )

    # 종합 성능 점수
    overall_performance_score = Column(
        DECIMAL(5, 4), nullable=True, comment="종합 성능 점수 (0.0 ~ 1.0)"
    )

    # =================================================================
    # 하이퍼파라미터 및 설정
    # =================================================================

    hyperparameters = Column(
        Text, nullable=True, comment="하이퍼파라미터 정보 (JSON 형태)"
    )

    model_architecture = Column(
        Text, nullable=True, comment="모델 구조 정보 (JSON 형태)"
    )

    training_config = Column(Text, nullable=True, comment="훈련 설정 정보 (JSON 형태)")

    # =================================================================
    # 상태 및 배포 정보
    # =================================================================

    status = Column(
        String(20),
        nullable=False,
        default="training",
        comment="모델 상태 (training, active, deprecated, failed)",
    )

    is_active = Column(
        Boolean, nullable=False, default=False, comment="현재 활성 모델 여부"
    )

    deployed_at = Column(DateTime, nullable=True, comment="배포 시점")

    deprecated_at = Column(DateTime, nullable=True, comment="사용 중단 시점")

    # =================================================================
    # 메타데이터
    # =================================================================

    description = Column(Text, nullable=True, comment="모델 설명")

    created_by = Column(String(100), nullable=True, comment="모델 생성자")

    tags = Column(Text, nullable=True, comment="모델 태그 (JSON 배열)")

    created_at = Column(DateTime, default=func.now(), comment="레코드 생성 시점")

    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), comment="레코드 수정 시점"
    )

    # =================================================================
    # 제약조건 및 인덱스
    # =================================================================

    __table_args__ = (
        # 중복 방지: 같은 이름과 버전의 모델은 1개만 허용
        UniqueConstraint("model_name", "model_version", name="uq_model_name_version"),
        # 모델 이름별 조회 최적화
        Index("idx_ml_model_name", "model_name"),
        # 심볼별 조회 최적화
        Index("idx_ml_model_symbol", "symbol"),
        # 활성 모델 조회 최적화
        Index("idx_ml_model_active", "is_active", "status"),
        # 모델 타입별 조회 최적화
        Index("idx_ml_model_type", "model_type"),
        # 성능 기반 조회 최적화
        Index("idx_ml_model_performance", "overall_performance_score"),
        # 훈련 날짜별 조회 최적화
        Index("idx_ml_model_training_date", "training_end_date"),
    )

    def __repr__(self):
        return (
            f"<MLModel("
            f"name={self.model_name}, "
            f"version={self.model_version}, "
            f"type={self.model_type}, "
            f"active={self.is_active}"
            f")>"
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        엔티티를 딕셔너리로 변환 (API 응답용)
        """
        return {
            "id": self.id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "model_type": self.model_type,
            "symbol": self.symbol,
            "file_info": {
                "model_path": self.model_path,
                "model_format": self.model_format,
                "model_size_mb": (
                    float(self.model_size_mb) if self.model_size_mb else None
                ),
                "checksum": self.checksum,
            },
            "training_info": {
                "training_start_date": (
                    self.training_start_date.isoformat()
                    if self.training_start_date
                    else None
                ),
                "training_end_date": (
                    self.training_end_date.isoformat()
                    if self.training_end_date
                    else None
                ),
                "training_duration_minutes": self.training_duration_minutes,
                "epochs_trained": self.epochs_trained,
                "early_stopped": self.early_stopped,
            },
            "data_info": {
                "training_data_start_date": (
                    self.training_data_start_date.isoformat()
                    if self.training_data_start_date
                    else None
                ),
                "training_data_end_date": (
                    self.training_data_end_date.isoformat()
                    if self.training_data_end_date
                    else None
                ),
                "training_samples": self.training_samples,
                "validation_samples": self.validation_samples,
                "test_samples": self.test_samples,
                "feature_count": self.feature_count,
                "window_size": self.window_size,
            },
            "performance": {
                "7d": {
                    "mse": (
                        float(self.performance_7d_mse)
                        if self.performance_7d_mse
                        else None
                    ),
                    "mae": (
                        float(self.performance_7d_mae)
                        if self.performance_7d_mae
                        else None
                    ),
                    "direction_accuracy": (
                        float(self.performance_7d_direction_accuracy)
                        if self.performance_7d_direction_accuracy
                        else None
                    ),
                },
                "14d": {
                    "mse": (
                        float(self.performance_14d_mse)
                        if self.performance_14d_mse
                        else None
                    ),
                    "mae": (
                        float(self.performance_14d_mae)
                        if self.performance_14d_mae
                        else None
                    ),
                    "direction_accuracy": (
                        float(self.performance_14d_direction_accuracy)
                        if self.performance_14d_direction_accuracy
                        else None
                    ),
                },
                "30d": {
                    "mse": (
                        float(self.performance_30d_mse)
                        if self.performance_30d_mse
                        else None
                    ),
                    "mae": (
                        float(self.performance_30d_mae)
                        if self.performance_30d_mae
                        else None
                    ),
                    "direction_accuracy": (
                        float(self.performance_30d_direction_accuracy)
                        if self.performance_30d_direction_accuracy
                        else None
                    ),
                },
                "overall_score": (
                    float(self.overall_performance_score)
                    if self.overall_performance_score
                    else None
                ),
            },
            "config": {
                "hyperparameters": self.get_hyperparameters(),
                "model_architecture": self.get_model_architecture(),
                "training_config": self.get_training_config(),
            },
            "status": {
                "status": self.status,
                "is_active": self.is_active,
                "deployed_at": (
                    self.deployed_at.isoformat() if self.deployed_at else None
                ),
                "deprecated_at": (
                    self.deprecated_at.isoformat() if self.deprecated_at else None
                ),
            },
            "metadata": {
                "description": self.description,
                "created_by": self.created_by,
                "tags": self.get_tags(),
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            },
        }

    def get_hyperparameters(self) -> Optional[Dict[str, Any]]:
        """하이퍼파라미터 정보를 파싱하여 반환"""
        if not self.hyperparameters:
            return None

        try:
            return json.loads(self.hyperparameters)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_hyperparameters(self, hyperparams: Dict[str, Any]) -> None:
        """하이퍼파라미터 정보를 JSON 문자열로 저장"""
        if hyperparams:
            self.hyperparameters = json.dumps(hyperparams)

    def get_model_architecture(self) -> Optional[Dict[str, Any]]:
        """모델 구조 정보를 파싱하여 반환"""
        if not self.model_architecture:
            return None

        try:
            return json.loads(self.model_architecture)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_model_architecture(self, architecture: Dict[str, Any]) -> None:
        """모델 구조 정보를 JSON 문자열로 저장"""
        if architecture:
            self.model_architecture = json.dumps(architecture)

    def get_training_config(self) -> Optional[Dict[str, Any]]:
        """훈련 설정 정보를 파싱하여 반환"""
        if not self.training_config:
            return None

        try:
            return json.loads(self.training_config)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_training_config(self, config: Dict[str, Any]) -> None:
        """훈련 설정 정보를 JSON 문자열로 저장"""
        if config:
            self.training_config = json.dumps(config)

    def get_tags(self) -> Optional[List[str]]:
        """태그 목록을 파싱하여 반환"""
        if not self.tags:
            return None

        try:
            return json.loads(self.tags)
        except (json.JSONDecodeError, TypeError):
            return None

    def set_tags(self, tag_list: List[str]) -> None:
        """태그 목록을 JSON 문자열로 저장"""
        if tag_list:
            self.tags = json.dumps(tag_list)

    def calculate_overall_performance_score(self) -> float:
        """
        종합 성능 점수 계산

        각 타임프레임의 방향 정확도를 가중 평균하여 계산
        (7일: 50%, 14일: 30%, 30일: 20%)
        """
        scores = []
        weights = []

        if self.performance_7d_direction_accuracy is not None:
            scores.append(float(self.performance_7d_direction_accuracy))
            weights.append(0.5)

        if self.performance_14d_direction_accuracy is not None:
            scores.append(float(self.performance_14d_direction_accuracy))
            weights.append(0.3)

        if self.performance_30d_direction_accuracy is not None:
            scores.append(float(self.performance_30d_direction_accuracy))
            weights.append(0.2)

        if not scores:
            return 0.0

        # 가중 평균 계산
        weighted_sum = sum(score * weight for score, weight in zip(scores, weights))
        total_weight = sum(weights)

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def update_performance_metrics(
        self, timeframe: str, mse: float, mae: float, direction_accuracy: float
    ) -> None:
        """
        특정 타임프레임의 성능 지표 업데이트

        Args:
            timeframe: 타임프레임 ('7d', '14d', '30d')
            mse: Mean Squared Error
            mae: Mean Absolute Error
            direction_accuracy: 방향 정확도
        """
        if timeframe == "7d":
            self.performance_7d_mse = mse
            self.performance_7d_mae = mae
            self.performance_7d_direction_accuracy = direction_accuracy
        elif timeframe == "14d":
            self.performance_14d_mse = mse
            self.performance_14d_mae = mae
            self.performance_14d_direction_accuracy = direction_accuracy
        elif timeframe == "30d":
            self.performance_30d_mse = mse
            self.performance_30d_mae = mae
            self.performance_30d_direction_accuracy = direction_accuracy

        # 종합 성능 점수 재계산
        self.overall_performance_score = self.calculate_overall_performance_score()

    def activate(self) -> None:
        """모델을 활성 상태로 변경"""
        self.is_active = True
        self.status = "active"
        self.deployed_at = func.now()

    def deactivate(self) -> None:
        """모델을 비활성 상태로 변경"""
        self.is_active = False
        self.status = "deprecated"
        self.deprecated_at = func.now()

    def is_better_than(self, other_model: "MLModel") -> bool:
        """
        다른 모델보다 성능이 좋은지 비교

        Args:
            other_model: 비교할 다른 모델

        Returns:
            현재 모델이 더 좋으면 True
        """
        if (
            not self.overall_performance_score
            or not other_model.overall_performance_score
        ):
            return False

        return float(self.overall_performance_score) > float(
            other_model.overall_performance_score
        )

    @classmethod
    def create_model(
        cls,
        model_name: str,
        model_version: str,
        model_type: str,
        symbol: str,
        model_path: str,
        training_start_date: datetime,
        training_end_date: datetime,
        epochs_trained: int,
        training_data_start_date: datetime,
        training_data_end_date: datetime,
        training_samples: int,
        validation_samples: int,
        test_samples: int,
        feature_count: int,
        window_size: int,
        hyperparameters: Optional[Dict[str, Any]] = None,
        model_architecture: Optional[Dict[str, Any]] = None,
        training_config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> "MLModel":
        """
        새로운 모델 메타데이터 생성

        Returns:
            생성된 MLModel 인스턴스
        """
        model = cls(
            model_name=model_name,
            model_version=model_version,
            model_type=model_type,
            symbol=symbol,
            model_path=model_path,
            training_start_date=training_start_date,
            training_end_date=training_end_date,
            epochs_trained=epochs_trained,
            training_data_start_date=training_data_start_date,
            training_data_end_date=training_data_end_date,
            training_samples=training_samples,
            validation_samples=validation_samples,
            test_samples=test_samples,
            feature_count=feature_count,
            window_size=window_size,
            description=description,
            created_by=created_by,
        )

        # 훈련 소요 시간 계산
        if training_start_date and training_end_date:
            duration = training_end_date - training_start_date
            model.training_duration_minutes = int(duration.total_seconds() / 60)

        # JSON 데이터 설정
        if hyperparameters:
            model.set_hyperparameters(hyperparameters)

        if model_architecture:
            model.set_model_architecture(model_architecture)

        if training_config:
            model.set_training_config(training_config)

        if tags:
            model.set_tags(tags)

        return model

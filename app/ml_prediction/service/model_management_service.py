"""
모델 관리 서비스

이 파일은 ML 모델의 버전 관리, 활성 모델 선택, 성능 기반 자동 교체 등
모델 라이프사이클 전반을 관리하는 서비스를 구현합니다.

주요 기능:
- 모델 버전 관리
- 활성 모델 선택 및 교체
- 성능 기반 자동 모델 교체
- 모델 메타데이터 관리
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import os
import shutil
from dataclasses import dataclass

from app.ml_prediction.ml.evaluation.evaluator import ModelEvaluator
from app.ml_prediction.infra.model.repository.ml_model_repository import (
    MLModelRepository,
)
from app.ml_prediction.infra.model.repository.ml_prediction_repository import (
    MLPredictionRepository,
)
from app.ml_prediction.infra.model.entity.ml_model import MLModel
from app.ml_prediction.config.ml_config import ml_settings
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ModelPerformanceThreshold:
    """모델 성능 임계값"""

    min_direction_accuracy: float = 0.55  # 최소 방향 정확도 (55%)
    max_avg_error_percent: float = 8.0  # 최대 평균 오차율 (8%)
    min_predictions_for_evaluation: int = 50  # 평가를 위한 최소 예측 수
    performance_degradation_threshold: float = 0.05  # 성능 저하 임계값 (5%p)


class ModelManagementService:
    """
    모델 관리 서비스

    ML 모델의 전체 라이프사이클을 관리합니다.
    """

    def __init__(self, config=None):
        """
        서비스 초기화

        Args:
            config: ML 설정
        """
        self.config = config or ml_settings
        self.evaluator = ModelEvaluator()
        self.performance_threshold = ModelPerformanceThreshold()

        logger.info(
            "model_management_service_initialized",
            model_storage_path=self.config.storage.base_model_path,
            performance_threshold=self.performance_threshold.__dict__,
        )

    def register_model(
        self,
        model_name: str,
        model_version: str,
        model_type: str,
        model_path: str,
        symbol: str,
        training_start_date: Optional[date] = None,
        training_end_date: Optional[date] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        training_metrics: Optional[Dict[str, float]] = None,
        set_as_active: bool = False,
    ) -> Dict[str, Any]:
        """
        모델 등록

        Args:
            model_name: 모델 이름
            model_version: 모델 버전
            model_type: 모델 타입
            model_path: 모델 파일 경로
            symbol: 심볼
            training_start_date: 훈련 시작 날짜
            training_end_date: 훈련 종료 날짜
            hyperparameters: 하이퍼파라미터
            training_metrics: 훈련 지표
            set_as_active: 활성 모델로 설정 여부

        Returns:
            등록 결과
        """
        logger.info(
            "model_registration_started",
            model_name=model_name,
            model_version=model_version,
            model_type=model_type,
            symbol=symbol,
            set_as_active=set_as_active,
        )

        session = SessionLocal()
        model_repo = MLModelRepository(session)

        try:
            # 기존 모델 확인
            existing_model = model_repo.find_by_name_and_version(
                model_name, model_version
            )

            if existing_model:
                logger.warning(
                    "model_already_exists",
                    model_name=model_name,
                    model_version=model_version,
                )
                return {
                    "status": "exists",
                    "message": f"Model {model_name} version {model_version} already exists",
                    "model_id": existing_model.id,
                }

            # 활성 모델로 설정하는 경우 기존 활성 모델 비활성화
            if set_as_active:
                self._deactivate_existing_models(model_repo, model_type, symbol)

            # 새 모델 엔티티 생성
            model_entity = MLModel(
                model_name=model_name,
                model_version=model_version,
                model_type=model_type,
                model_path=model_path,
                symbol=symbol,
                training_start_date=training_start_date,
                training_end_date=training_end_date,
                hyperparameters=hyperparameters,
                training_metrics=training_metrics,
                is_active=set_as_active,
                created_at=datetime.now(),
            )

            # 모델 저장
            saved_model = model_repo.save(model_entity)

            logger.info(
                "model_registered_successfully",
                model_id=saved_model.id,
                model_name=model_name,
                model_version=model_version,
                is_active=set_as_active,
            )

            return {
                "status": "success",
                "model_id": saved_model.id,
                "model_name": model_name,
                "model_version": model_version,
                "is_active": set_as_active,
                "registered_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(
                "model_registration_failed",
                model_name=model_name,
                model_version=model_version,
                error=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            session.close()

    def set_active_model(self, model_name: str, model_version: str) -> Dict[str, Any]:
        """
        활성 모델 설정

        Args:
            model_name: 모델 이름
            model_version: 모델 버전

        Returns:
            설정 결과
        """
        logger.info(
            "setting_active_model", model_name=model_name, model_version=model_version
        )

        session = SessionLocal()
        model_repo = MLModelRepository(session)

        try:
            # 대상 모델 조회
            target_model = model_repo.find_by_name_and_version(
                model_name, model_version
            )

            if not target_model:
                return {
                    "status": "failed",
                    "error": f"Model {model_name} version {model_version} not found",
                }

            # 기존 활성 모델 비활성화
            self._deactivate_existing_models(
                model_repo, target_model.model_type, target_model.symbol
            )

            # 새 모델 활성화
            target_model.is_active = True
            target_model.activated_at = datetime.now()
            model_repo.update(target_model)

            logger.info(
                "active_model_set_successfully",
                model_id=target_model.id,
                model_name=model_name,
                model_version=model_version,
            )

            return {
                "status": "success",
                "model_id": target_model.id,
                "model_name": model_name,
                "model_version": model_version,
                "activated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(
                "set_active_model_failed",
                model_name=model_name,
                model_version=model_version,
                error=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            session.close()

    def get_active_model(
        self, model_type: str, symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        활성 모델 조회

        Args:
            model_type: 모델 타입
            symbol: 심볼

        Returns:
            활성 모델 정보
        """
        session = SessionLocal()
        model_repo = MLModelRepository(session)

        try:
            active_model = model_repo.find_active_model(model_type, symbol)

            if not active_model:
                return None

            return {
                "model_id": active_model.id,
                "model_name": active_model.model_name,
                "model_version": active_model.model_version,
                "model_type": active_model.model_type,
                "model_path": active_model.model_path,
                "symbol": active_model.symbol,
                "training_start_date": (
                    active_model.training_start_date.isoformat()
                    if active_model.training_start_date
                    else None
                ),
                "training_end_date": (
                    active_model.training_end_date.isoformat()
                    if active_model.training_end_date
                    else None
                ),
                "hyperparameters": active_model.hyperparameters,
                "training_metrics": active_model.training_metrics,
                "activated_at": (
                    active_model.activated_at.isoformat()
                    if active_model.activated_at
                    else None
                ),
                "created_at": active_model.created_at.isoformat(),
            }

        finally:
            session.close()

    def list_models(
        self,
        symbol: Optional[str] = None,
        model_type: Optional[str] = None,
        active_only: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        모델 목록 조회

        Args:
            symbol: 심볼 필터
            model_type: 모델 타입 필터
            active_only: 활성 모델만 조회
            limit: 최대 조회 수

        Returns:
            모델 목록
        """
        session = SessionLocal()
        model_repo = MLModelRepository(session)

        try:
            models = model_repo.find_models(
                symbol=symbol,
                model_type=model_type,
                active_only=active_only,
                limit=limit,
            )

            model_list = []
            for model in models:
                model_list.append(
                    {
                        "model_id": model.id,
                        "model_name": model.model_name,
                        "model_version": model.model_version,
                        "model_type": model.model_type,
                        "symbol": model.symbol,
                        "is_active": model.is_active,
                        "training_end_date": (
                            model.training_end_date.isoformat()
                            if model.training_end_date
                            else None
                        ),
                        "activated_at": (
                            model.activated_at.isoformat()
                            if model.activated_at
                            else None
                        ),
                        "created_at": model.created_at.isoformat(),
                    }
                )

            return model_list

        finally:
            session.close()

    def _deactivate_existing_models(
        self, model_repo: MLModelRepository, model_type: str, symbol: str
    ) -> None:
        """기존 활성 모델들 비활성화"""
        existing_active_models = model_repo.find_models(
            symbol=symbol, model_type=model_type, active_only=True
        )

        for model in existing_active_models:
            model.is_active = False
            model.deactivated_at = datetime.now()
            model_repo.update(model)

            logger.info(
                "model_deactivated",
                model_id=model.id,
                model_name=model.model_name,
                model_version=model.model_version,
            )

    def get_service_status(self) -> Dict[str, Any]:
        """서비스 상태 조회"""
        return {
            "service": "ModelManagementService",
            "status": "running",
            "config": {
                "model_storage_path": self.config.storage.base_model_path,
                "performance_threshold": self.performance_threshold.__dict__,
            },
            "components": {"evaluator": "ready"},
            "timestamp": datetime.now().isoformat(),
        }

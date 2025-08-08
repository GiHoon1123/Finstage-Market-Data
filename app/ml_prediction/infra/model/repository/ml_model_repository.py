"""
ML 모델 메타데이터 리포지토리

이 파일은 ML 모델 메타데이터의 CRUD 작업과 모델 버전 관리를 담당합니다.
모델의 생명주기 관리, 성능 추적, 활성 모델 선택 등의 기능을 제공합니다.

주요 기능:
- 모델 메타데이터 저장 및 조회
- 모델 버전 관리 및 활성 모델 선택
- 성능 기반 모델 비교 및 자동 교체
- 모델 배포 상태 관리
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.exc import IntegrityError

from app.ml_prediction.infra.model.entity.ml_model import MLModel
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MLModelRepository:
    """
    ML 모델 메타데이터 리포지토리

    MLModel 엔티티에 대한 모든 데이터베이스 작업을 담당합니다.
    모델 버전 관리와 성능 기반 모델 선택 기능을 제공합니다.
    """

    def __init__(self, session: Session):
        """
        리포지토리 초기화

        Args:
            session: SQLAlchemy 세션
        """
        self.session = session

    # =================================================================
    # 기본 CRUD 작업
    # =================================================================

    def save(self, model: MLModel) -> Optional[MLModel]:
        """
        모델 메타데이터 저장

        Args:
            model: 저장할 모델 메타데이터

        Returns:
            저장된 모델 메타데이터 (실패 시 None)
        """
        try:
            self.session.add(model)
            self.session.commit()
            self.session.refresh(model)

            logger.info(
                "ml_model_saved",
                model_id=model.id,
                model_name=model.model_name,
                model_version=model.model_version,
                symbol=model.symbol,
            )

            return model

        except IntegrityError as e:
            self.session.rollback()
            logger.warning(
                "ml_model_save_failed_duplicate",
                model_name=model.model_name,
                model_version=model.model_version,
                error=str(e),
            )
            return None

        except Exception as e:
            self.session.rollback()
            logger.error(
                "ml_model_save_failed", model_name=model.model_name, error=str(e)
            )
            raise

    def find_by_id(self, model_id: int) -> Optional[MLModel]:
        """
        ID로 모델 조회

        Args:
            model_id: 모델 ID

        Returns:
            모델 메타데이터 (없으면 None)
        """
        return self.session.query(MLModel).filter(MLModel.id == model_id).first()

    def find_by_name_and_version(
        self, model_name: str, model_version: str
    ) -> Optional[MLModel]:
        """
        모델 이름과 버전으로 조회

        Args:
            model_name: 모델 이름
            model_version: 모델 버전

        Returns:
            모델 메타데이터 (없으면 None)
        """
        return (
            self.session.query(MLModel)
            .filter(
                and_(
                    MLModel.model_name == model_name,
                    MLModel.model_version == model_version,
                )
            )
            .first()
        )

    def update(self, model: MLModel) -> bool:
        """
        모델 메타데이터 업데이트

        Args:
            model: 업데이트할 모델

        Returns:
            업데이트 성공 여부
        """
        try:
            self.session.commit()

            logger.info(
                "ml_model_updated",
                model_id=model.id,
                model_name=model.model_name,
                model_version=model.model_version,
            )

            return True

        except Exception as e:
            self.session.rollback()
            logger.error("ml_model_update_failed", model_id=model.id, error=str(e))
            return False

    def delete_by_id(self, model_id: int) -> bool:
        """
        ID로 모델 삭제

        Args:
            model_id: 모델 ID

        Returns:
            삭제 성공 여부
        """
        try:
            model = self.find_by_id(model_id)
            if not model:
                return False

            self.session.delete(model)
            self.session.commit()

            logger.info(
                "ml_model_deleted",
                model_id=model_id,
                model_name=model.model_name,
                model_version=model.model_version,
            )

            return True

        except Exception as e:
            self.session.rollback()
            logger.error("ml_model_delete_failed", model_id=model_id, error=str(e))
            return False

    # =================================================================
    # 모델 버전 관리
    # =================================================================

    def find_active_model(
        self, model_type: str, symbol: Optional[str] = None
    ) -> Optional[MLModel]:
        """
        활성 모델 조회

        Args:
            model_type: 모델 타입
            symbol: 심볼 (선택사항)

        Returns:
            활성 모델 (없으면 None)
        """
        query = self.session.query(MLModel).filter(
            and_(
                MLModel.model_type == model_type,
                MLModel.is_active == True,
                MLModel.status == "active",
            )
        )

        if symbol:
            query = query.filter(MLModel.symbol == symbol)

        return query.first()

    def find_all_versions(
        self, model_name: str, order_desc: bool = True
    ) -> List[MLModel]:
        """
        모델의 모든 버전 조회

        Args:
            model_name: 모델 이름
            order_desc: 내림차순 정렬 여부

        Returns:
            모델 버전 목록
        """
        query = self.session.query(MLModel).filter(MLModel.model_name == model_name)

        if order_desc:
            query = query.order_by(desc(MLModel.created_at))
        else:
            query = query.order_by(asc(MLModel.created_at))

        return query.all()

    def find_latest_version(self, model_name: str) -> Optional[MLModel]:
        """
        모델의 최신 버전 조회

        Args:
            model_name: 모델 이름

        Returns:
            최신 버전 모델 (없으면 None)
        """
        return (
            self.session.query(MLModel)
            .filter(MLModel.model_name == model_name)
            .order_by(desc(MLModel.created_at))
            .first()
        )

    def find_best_performing_model(
        self, model_type: str, symbol: Optional[str] = None, days: int = 90
    ) -> Optional[MLModel]:
        """
        최고 성능 모델 조회

        Args:
            model_type: 모델 타입
            symbol: 심볼 (선택사항)
            days: 최근 며칠간의 모델 중에서 선택

        Returns:
            최고 성능 모델 (없으면 None)
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        query = self.session.query(MLModel).filter(
            and_(
                MLModel.model_type == model_type,
                MLModel.status.in_(["active", "deprecated"]),
                MLModel.training_end_date >= cutoff_date,
                MLModel.overall_performance_score.isnot(None),
            )
        )

        if symbol:
            query = query.filter(MLModel.symbol == symbol)

        return query.order_by(desc(MLModel.overall_performance_score)).first()

    def activate_model(self, model_id: int) -> bool:
        """
        모델을 활성 상태로 변경 (기존 활성 모델은 비활성화)

        Args:
            model_id: 활성화할 모델 ID

        Returns:
            활성화 성공 여부
        """
        try:
            model = self.find_by_id(model_id)
            if not model:
                logger.warning("ml_model_not_found_for_activation", model_id=model_id)
                return False

            # 같은 타입과 심볼의 기존 활성 모델들을 비활성화
            self.session.query(MLModel).filter(
                and_(
                    MLModel.model_type == model.model_type,
                    MLModel.symbol == model.symbol,
                    MLModel.is_active == True,
                )
            ).update(
                {
                    "is_active": False,
                    "status": "deprecated",
                    "deprecated_at": func.now(),
                }
            )

            # 새 모델 활성화
            model.activate()
            self.session.commit()

            logger.info(
                "ml_model_activated",
                model_id=model_id,
                model_name=model.model_name,
                model_version=model.model_version,
            )

            return True

        except Exception as e:
            self.session.rollback()
            logger.error("ml_model_activation_failed", model_id=model_id, error=str(e))
            return False

    def deactivate_model(self, model_id: int) -> bool:
        """
        모델을 비활성 상태로 변경

        Args:
            model_id: 비활성화할 모델 ID

        Returns:
            비활성화 성공 여부
        """
        try:
            model = self.find_by_id(model_id)
            if not model:
                return False

            model.deactivate()
            self.session.commit()

            logger.info(
                "ml_model_deactivated",
                model_id=model_id,
                model_name=model.model_name,
                model_version=model.model_version,
            )

            return True

        except Exception as e:
            self.session.rollback()
            logger.error(
                "ml_model_deactivation_failed", model_id=model_id, error=str(e)
            )
            return False

    def auto_select_best_model(
        self, model_type: str, symbol: str, performance_threshold: float = 0.6
    ) -> Optional[MLModel]:
        """
        성능 기준에 따른 최적 모델 자동 선택 및 활성화

        Args:
            model_type: 모델 타입
            symbol: 심볼
            performance_threshold: 최소 성능 임계값

        Returns:
            선택된 모델 (없으면 None)
        """
        try:
            # 성능 임계값을 만족하는 모델들 조회
            candidates = (
                self.session.query(MLModel)
                .filter(
                    and_(
                        MLModel.model_type == model_type,
                        MLModel.symbol == symbol,
                        MLModel.status.in_(["active", "deprecated"]),
                        MLModel.overall_performance_score >= performance_threshold,
                    )
                )
                .order_by(desc(MLModel.overall_performance_score))
                .all()
            )

            if not candidates:
                logger.warning(
                    "no_models_meet_performance_threshold",
                    model_type=model_type,
                    symbol=symbol,
                    threshold=performance_threshold,
                )
                return None

            best_model = candidates[0]
            current_active = self.find_active_model(model_type, symbol)

            # 현재 활성 모델보다 성능이 좋은 경우에만 교체
            if not current_active or best_model.is_better_than(current_active):
                if self.activate_model(best_model.id):
                    logger.info(
                        "best_model_auto_selected",
                        model_id=best_model.id,
                        model_name=best_model.model_name,
                        model_version=best_model.model_version,
                        performance_score=best_model.overall_performance_score,
                    )
                    return best_model

            return current_active

        except Exception as e:
            logger.error(
                "auto_model_selection_failed",
                model_type=model_type,
                symbol=symbol,
                error=str(e),
            )
            return None

    # =================================================================
    # 성능 및 통계 조회
    # =================================================================

    def find_by_performance_range(
        self,
        min_score: float,
        max_score: float = 1.0,
        model_type: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[MLModel]:
        """
        성능 점수 범위로 모델 조회

        Args:
            min_score: 최소 성능 점수
            max_score: 최대 성능 점수
            model_type: 모델 타입 (선택사항)
            symbol: 심볼 (선택사항)

        Returns:
            조건에 맞는 모델 목록
        """
        query = self.session.query(MLModel).filter(
            and_(
                MLModel.overall_performance_score >= min_score,
                MLModel.overall_performance_score <= max_score,
            )
        )

        if model_type:
            query = query.filter(MLModel.model_type == model_type)

        if symbol:
            query = query.filter(MLModel.symbol == symbol)

        return query.order_by(desc(MLModel.overall_performance_score)).all()

    def get_model_performance_history(self, model_name: str) -> List[Dict[str, Any]]:
        """
        모델의 버전별 성능 이력 조회

        Args:
            model_name: 모델 이름

        Returns:
            버전별 성능 이력
        """
        models = self.find_all_versions(model_name, order_desc=False)

        history = []
        for model in models:
            history.append(
                {
                    "version": model.model_version,
                    "training_date": (
                        model.training_end_date.isoformat()
                        if model.training_end_date
                        else None
                    ),
                    "overall_score": (
                        float(model.overall_performance_score)
                        if model.overall_performance_score
                        else None
                    ),
                    "performance_7d": (
                        float(model.performance_7d_direction_accuracy)
                        if model.performance_7d_direction_accuracy
                        else None
                    ),
                    "performance_14d": (
                        float(model.performance_14d_direction_accuracy)
                        if model.performance_14d_direction_accuracy
                        else None
                    ),
                    "performance_30d": (
                        float(model.performance_30d_direction_accuracy)
                        if model.performance_30d_direction_accuracy
                        else None
                    ),
                    "is_active": model.is_active,
                    "status": model.status,
                }
            )

        return history

    def get_training_statistics(self, days: int = 30) -> Dict[str, Any]:
        """
        최근 훈련 통계 조회

        Args:
            days: 최근 며칠간의 통계

        Returns:
            훈련 통계 정보
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # 기본 통계
        total_models = (
            self.session.query(MLModel)
            .filter(MLModel.training_end_date >= cutoff_date)
            .count()
        )

        active_models = (
            self.session.query(MLModel)
            .filter(
                and_(
                    MLModel.training_end_date >= cutoff_date, MLModel.is_active == True
                )
            )
            .count()
        )

        # 평균 성능 점수
        avg_performance = (
            self.session.query(func.avg(MLModel.overall_performance_score))
            .filter(
                and_(
                    MLModel.training_end_date >= cutoff_date,
                    MLModel.overall_performance_score.isnot(None),
                )
            )
            .scalar()
        )

        # 평균 훈련 시간
        avg_training_time = (
            self.session.query(func.avg(MLModel.training_duration_minutes))
            .filter(
                and_(
                    MLModel.training_end_date >= cutoff_date,
                    MLModel.training_duration_minutes.isnot(None),
                )
            )
            .scalar()
        )

        # 모델 타입별 분포
        type_distribution = (
            self.session.query(
                MLModel.model_type, func.count(MLModel.id).label("count")
            )
            .filter(MLModel.training_end_date >= cutoff_date)
            .group_by(MLModel.model_type)
            .all()
        )

        return {
            "total_models": total_models,
            "active_models": active_models,
            "avg_performance_score": float(avg_performance) if avg_performance else 0.0,
            "avg_training_time_minutes": (
                float(avg_training_time) if avg_training_time else 0.0
            ),
            "type_distribution": {
                model_type: count for model_type, count in type_distribution
            },
        }

    # =================================================================
    # 유틸리티 메서드
    # =================================================================

    def count_by_symbol(self, symbol: str) -> int:
        """
        심볼별 모델 개수 조회

        Args:
            symbol: 심볼

        Returns:
            모델 개수
        """
        return self.session.query(MLModel).filter(MLModel.symbol == symbol).count()

    def count_by_type(self, model_type: str) -> int:
        """
        모델 타입별 개수 조회

        Args:
            model_type: 모델 타입

        Returns:
            모델 개수
        """
        return (
            self.session.query(MLModel).filter(MLModel.model_type == model_type).count()
        )

    def find_models_by_status(self, status: str) -> List[MLModel]:
        """
        상태별 모델 조회

        Args:
            status: 모델 상태

        Returns:
            해당 상태의 모델 목록
        """
        return (
            self.session.query(MLModel)
            .filter(MLModel.status == status)
            .order_by(desc(MLModel.updated_at))
            .all()
        )

    def cleanup_old_models(self, model_name: str, keep_versions: int = 5) -> int:
        """
        오래된 모델 버전 정리 (최신 N개 버전만 유지)

        Args:
            model_name: 모델 이름
            keep_versions: 유지할 버전 수

        Returns:
            삭제된 모델 수
        """
        try:
            # 최신 버전들을 제외한 오래된 버전들 조회
            models_to_keep = (
                self.session.query(MLModel)
                .filter(MLModel.model_name == model_name)
                .order_by(desc(MLModel.created_at))
                .limit(keep_versions)
                .all()
            )

            keep_ids = [model.id for model in models_to_keep]

            # 활성 모델은 삭제하지 않음
            active_models = (
                self.session.query(MLModel)
                .filter(
                    and_(MLModel.model_name == model_name, MLModel.is_active == True)
                )
                .all()
            )

            for active_model in active_models:
                if active_model.id not in keep_ids:
                    keep_ids.append(active_model.id)

            # 삭제할 모델들 조회
            models_to_delete = (
                self.session.query(MLModel)
                .filter(
                    and_(MLModel.model_name == model_name, ~MLModel.id.in_(keep_ids))
                )
                .all()
            )

            deleted_count = 0
            for model in models_to_delete:
                self.session.delete(model)
                deleted_count += 1

            self.session.commit()

            logger.info(
                "old_models_cleaned_up",
                model_name=model_name,
                deleted_count=deleted_count,
                kept_versions=keep_versions,
            )

            return deleted_count

        except Exception as e:
            self.session.rollback()
            logger.error("model_cleanup_failed", model_name=model_name, error=str(e))
            return 0

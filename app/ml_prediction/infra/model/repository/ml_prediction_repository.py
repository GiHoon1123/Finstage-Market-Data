"""
ML 예측 결과 리포지토리

이 파일은 ML 예측 결과 데이터의 CRUD 작업과 복잡한 조회 로직을 담당합니다.
멀티 타임프레임 예측 결과의 저장, 조회, 업데이트, 성능 분석을 지원합니다.

주요 기능:
- 멀티 타임프레임 예측 결과 저장 및 조회
- 배치 단위 예측 결과 관리
- 실제 결과와의 비교 및 정확도 계산
- 성능 분석을 위한 집계 쿼리
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.exc import IntegrityError

from app.ml_prediction.infra.model.entity.ml_prediction import MLPrediction
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MLPredictionRepository:
    """
    ML 예측 결과 리포지토리

    MLPrediction 엔티티에 대한 모든 데이터베이스 작업을 담당합니다.
    복잡한 조회 로직과 성능 분석 기능을 제공합니다.
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

    def save(self, prediction: MLPrediction) -> Optional[MLPrediction]:
        """
        예측 결과 저장

        Args:
            prediction: 저장할 예측 결과

        Returns:
            저장된 예측 결과 (실패 시 None)
        """
        try:
            self.session.add(prediction)
            self.session.commit()
            self.session.refresh(prediction)

            logger.info(
                "ml_prediction_saved",
                prediction_id=prediction.id,
                symbol=prediction.symbol,
                timeframe=prediction.prediction_timeframe,
                batch_id=prediction.batch_id,
            )

            return prediction

        except IntegrityError as e:
            self.session.rollback()
            logger.warning(
                "ml_prediction_save_failed_duplicate",
                symbol=prediction.symbol,
                prediction_date=prediction.prediction_date,
                timeframe=prediction.prediction_timeframe,
                error=str(e),
            )
            return None

        except Exception as e:
            self.session.rollback()
            logger.error(
                "ml_prediction_save_failed", symbol=prediction.symbol, error=str(e)
            )
            raise

    def save_batch(self, predictions: List[MLPrediction]) -> List[MLPrediction]:
        """
        여러 예측 결과를 배치로 저장

        Args:
            predictions: 저장할 예측 결과 목록

        Returns:
            성공적으로 저장된 예측 결과 목록
        """
        saved_predictions = []

        try:
            for prediction in predictions:
                self.session.add(prediction)

            self.session.commit()

            for prediction in predictions:
                self.session.refresh(prediction)
                saved_predictions.append(prediction)

            logger.info(
                "ml_prediction_batch_saved",
                count=len(saved_predictions),
                batch_id=predictions[0].batch_id if predictions else None,
            )

            return saved_predictions

        except Exception as e:
            self.session.rollback()
            logger.error(
                "ml_prediction_batch_save_failed", count=len(predictions), error=str(e)
            )
            raise

    def find_by_id(self, prediction_id: int) -> Optional[MLPrediction]:
        """
        ID로 예측 결과 조회

        Args:
            prediction_id: 예측 결과 ID

        Returns:
            예측 결과 (없으면 None)
        """
        return (
            self.session.query(MLPrediction)
            .filter(MLPrediction.id == prediction_id)
            .first()
        )

    def find_by_batch_id(self, batch_id: str) -> List[MLPrediction]:
        """
        배치 ID로 관련된 모든 예측 결과 조회

        Args:
            batch_id: 배치 ID

        Returns:
            해당 배치의 모든 예측 결과
        """
        return (
            self.session.query(MLPrediction)
            .filter(MLPrediction.batch_id == batch_id)
            .order_by(MLPrediction.prediction_timeframe)
            .all()
        )

    def update_actual_result(self, prediction_id: int, actual_price: float) -> bool:
        """
        실제 결과로 예측 정확도 업데이트

        Args:
            prediction_id: 예측 결과 ID
            actual_price: 실제 가격

        Returns:
            업데이트 성공 여부
        """
        try:
            prediction = self.find_by_id(prediction_id)
            if not prediction:
                logger.warning(
                    "ml_prediction_not_found_for_update", prediction_id=prediction_id
                )
                return False

            prediction.update_actual_result(actual_price)
            self.session.commit()

            logger.info(
                "ml_prediction_actual_result_updated",
                prediction_id=prediction_id,
                actual_price=actual_price,
                is_direction_correct=prediction.is_direction_correct,
                price_error_percent=prediction.price_error_percent,
            )

            return True

        except Exception as e:
            self.session.rollback()
            logger.error(
                "ml_prediction_actual_result_update_failed",
                prediction_id=prediction_id,
                error=str(e),
            )
            return False

    def delete_by_id(self, prediction_id: int) -> bool:
        """
        ID로 예측 결과 삭제

        Args:
            prediction_id: 예측 결과 ID

        Returns:
            삭제 성공 여부
        """
        try:
            prediction = self.find_by_id(prediction_id)
            if not prediction:
                return False

            self.session.delete(prediction)
            self.session.commit()

            logger.info("ml_prediction_deleted", prediction_id=prediction_id)

            return True

        except Exception as e:
            self.session.rollback()
            logger.error(
                "ml_prediction_delete_failed", prediction_id=prediction_id, error=str(e)
            )
            return False

    # =================================================================
    # 조회 및 필터링
    # =================================================================

    def find_by_symbol_and_date_range(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: Optional[str] = None,
        order_desc: bool = True,
    ) -> List[MLPrediction]:
        """
        심볼과 날짜 범위로 예측 결과 조회

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            timeframe: 특정 타임프레임 (선택사항)
            order_desc: 내림차순 정렬 여부

        Returns:
            조건에 맞는 예측 결과 목록
        """
        query = self.session.query(MLPrediction).filter(
            and_(
                MLPrediction.symbol == symbol,
                MLPrediction.prediction_date >= start_date,
                MLPrediction.prediction_date <= end_date,
            )
        )

        if timeframe:
            query = query.filter(MLPrediction.prediction_timeframe == timeframe)

        if order_desc:
            query = query.order_by(desc(MLPrediction.prediction_date))
        else:
            query = query.order_by(asc(MLPrediction.prediction_date))

        return query.all()

    def find_by_target_date(
        self, target_date: date, symbol: Optional[str] = None
    ) -> List[MLPrediction]:
        """
        타겟 날짜로 예측 결과 조회 (실제 결과 업데이트용)

        Args:
            target_date: 타겟 날짜
            symbol: 심볼 (선택사항)

        Returns:
            해당 날짜를 타겟으로 하는 예측 결과 목록
        """
        query = self.session.query(MLPrediction).filter(
            MLPrediction.target_date == target_date
        )

        if symbol:
            query = query.filter(MLPrediction.symbol == symbol)

        return query.all()

    def find_pending_updates(self, days_old: int = 1) -> List[MLPrediction]:
        """
        실제 결과 업데이트가 필요한 예측 결과 조회

        Args:
            days_old: 며칠 이전까지의 예측을 대상으로 할지

        Returns:
            업데이트가 필요한 예측 결과 목록
        """
        cutoff_date = date.today() - timedelta(days=days_old)

        return (
            self.session.query(MLPrediction)
            .filter(
                and_(
                    MLPrediction.target_date <= cutoff_date,
                    MLPrediction.actual_price.is_(None),
                )
            )
            .order_by(MLPrediction.target_date)
            .all()
        )

    def find_recent_predictions(
        self, symbol: str, days: int = 30, limit: int = 100
    ) -> List[MLPrediction]:
        """
        최근 예측 결과 조회

        Args:
            symbol: 심볼
            days: 최근 며칠간의 데이터
            limit: 최대 결과 수

        Returns:
            최근 예측 결과 목록
        """
        start_date = date.today() - timedelta(days=days)

        return (
            self.session.query(MLPrediction)
            .filter(
                and_(
                    MLPrediction.symbol == symbol,
                    MLPrediction.prediction_date >= start_date,
                )
            )
            .order_by(desc(MLPrediction.prediction_date))
            .limit(limit)
            .all()
        )

    def find_by_model_version(
        self, model_version: str, symbol: Optional[str] = None, limit: int = 1000
    ) -> List[MLPrediction]:
        """
        모델 버전별 예측 결과 조회

        Args:
            model_version: 모델 버전
            symbol: 심볼 (선택사항)
            limit: 최대 결과 수

        Returns:
            해당 모델 버전의 예측 결과 목록
        """
        query = self.session.query(MLPrediction).filter(
            MLPrediction.model_version == model_version
        )

        if symbol:
            query = query.filter(MLPrediction.symbol == symbol)

        return query.order_by(desc(MLPrediction.prediction_date)).limit(limit).all()

    # =================================================================
    # 성능 분석 및 집계
    # =================================================================

    def get_accuracy_metrics(
        self, symbol: str, timeframe: str, days: int = 90
    ) -> Dict[str, float]:
        """
        특정 기간의 예측 정확도 지표 계산

        Args:
            symbol: 심볼
            timeframe: 타임프레임
            days: 분석 기간 (일)

        Returns:
            정확도 지표 딕셔너리
        """
        start_date = date.today() - timedelta(days=days)

        # 실제 결과가 있는 예측만 조회
        predictions = (
            self.session.query(MLPrediction)
            .filter(
                and_(
                    MLPrediction.symbol == symbol,
                    MLPrediction.prediction_timeframe == timeframe,
                    MLPrediction.prediction_date >= start_date,
                    MLPrediction.actual_price.isnot(None),
                )
            )
            .all()
        )

        if not predictions:
            return {
                "total_predictions": 0,
                "direction_accuracy": 0.0,
                "avg_price_error_percent": 0.0,
                "avg_confidence_score": 0.0,
                "avg_quality_score": 0.0,
            }

        # 지표 계산
        total_predictions = len(predictions)
        correct_directions = sum(1 for p in predictions if p.is_direction_correct)
        direction_accuracy = correct_directions / total_predictions

        price_errors = [
            float(p.price_error_percent)
            for p in predictions
            if p.price_error_percent is not None
        ]
        avg_price_error = sum(price_errors) / len(price_errors) if price_errors else 0.0

        confidence_scores = [float(p.confidence_score) for p in predictions]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        quality_scores = [p.get_prediction_quality_score() for p in predictions]
        avg_quality = sum(quality_scores) / len(quality_scores)

        return {
            "total_predictions": total_predictions,
            "direction_accuracy": direction_accuracy,
            "avg_price_error_percent": avg_price_error,
            "avg_confidence_score": avg_confidence,
            "avg_quality_score": avg_quality,
        }

    def get_performance_by_timeframe(
        self, symbol: str, days: int = 90
    ) -> Dict[str, Dict[str, float]]:
        """
        타임프레임별 성능 비교

        Args:
            symbol: 심볼
            days: 분석 기간 (일)

        Returns:
            타임프레임별 성능 지표
        """
        timeframes = ["7d", "14d", "30d"]
        results = {}

        for timeframe in timeframes:
            results[timeframe] = self.get_accuracy_metrics(symbol, timeframe, days)

        return results

    def get_model_performance_comparison(
        self, symbol: str, days: int = 90
    ) -> Dict[str, Dict[str, float]]:
        """
        모델 버전별 성능 비교

        Args:
            symbol: 심볼
            days: 분석 기간 (일)

        Returns:
            모델 버전별 성능 지표
        """
        start_date = date.today() - timedelta(days=days)

        # 해당 기간의 모든 모델 버전 조회
        model_versions = (
            self.session.query(MLPrediction.model_version)
            .filter(
                and_(
                    MLPrediction.symbol == symbol,
                    MLPrediction.prediction_date >= start_date,
                    MLPrediction.actual_price.isnot(None),
                )
            )
            .distinct()
            .all()
        )

        results = {}

        for (model_version,) in model_versions:
            # 각 모델 버전별 성능 계산
            predictions = (
                self.session.query(MLPrediction)
                .filter(
                    and_(
                        MLPrediction.symbol == symbol,
                        MLPrediction.model_version == model_version,
                        MLPrediction.prediction_date >= start_date,
                        MLPrediction.actual_price.isnot(None),
                    )
                )
                .all()
            )

            if predictions:
                total_predictions = len(predictions)
                correct_directions = sum(
                    1 for p in predictions if p.is_direction_correct
                )
                direction_accuracy = correct_directions / total_predictions

                quality_scores = [p.get_prediction_quality_score() for p in predictions]
                avg_quality = sum(quality_scores) / len(quality_scores)

                results[model_version] = {
                    "total_predictions": total_predictions,
                    "direction_accuracy": direction_accuracy,
                    "avg_quality_score": avg_quality,
                }

        return results

    def get_daily_performance_trend(
        self, symbol: str, timeframe: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        일별 성능 트렌드 조회

        Args:
            symbol: 심볼
            timeframe: 타임프레임
            days: 분석 기간 (일)

        Returns:
            일별 성능 데이터 목록
        """
        start_date = date.today() - timedelta(days=days)

        # 일별 집계 쿼리
        daily_stats = (
            self.session.query(
                MLPrediction.prediction_date,
                func.count(MLPrediction.id).label("total_predictions"),
                func.sum(
                    func.case([(MLPrediction.is_direction_correct == True, 1)], else_=0)
                ).label("correct_predictions"),
                func.avg(MLPrediction.confidence_score).label("avg_confidence"),
                func.avg(MLPrediction.price_error_percent).label("avg_price_error"),
            )
            .filter(
                and_(
                    MLPrediction.symbol == symbol,
                    MLPrediction.prediction_timeframe == timeframe,
                    MLPrediction.prediction_date >= start_date,
                    MLPrediction.actual_price.isnot(None),
                )
            )
            .group_by(MLPrediction.prediction_date)
            .order_by(MLPrediction.prediction_date)
            .all()
        )

        results = []
        for stat in daily_stats:
            direction_accuracy = (
                float(stat.correct_predictions) / float(stat.total_predictions)
                if stat.total_predictions > 0
                else 0.0
            )

            results.append(
                {
                    "date": stat.prediction_date.isoformat(),
                    "total_predictions": stat.total_predictions,
                    "direction_accuracy": direction_accuracy,
                    "avg_confidence": (
                        float(stat.avg_confidence) if stat.avg_confidence else 0.0
                    ),
                    "avg_price_error": (
                        float(stat.avg_price_error) if stat.avg_price_error else 0.0
                    ),
                }
            )

        return results

    # =================================================================
    # 유틸리티 메서드
    # =================================================================

    def count_by_symbol(self, symbol: str) -> int:
        """
        심볼별 예측 결과 개수 조회

        Args:
            symbol: 심볼

        Returns:
            예측 결과 개수
        """
        return (
            self.session.query(MLPrediction)
            .filter(MLPrediction.symbol == symbol)
            .count()
        )

    def count_by_timeframe(self, symbol: str, timeframe: str) -> int:
        """
        심볼과 타임프레임별 예측 결과 개수 조회

        Args:
            symbol: 심볼
            timeframe: 타임프레임

        Returns:
            예측 결과 개수
        """
        return (
            self.session.query(MLPrediction)
            .filter(
                and_(
                    MLPrediction.symbol == symbol,
                    MLPrediction.prediction_timeframe == timeframe,
                )
            )
            .count()
        )

    def get_date_range_by_symbol(self, symbol: str) -> Optional[Dict[str, str]]:
        """
        심볼별 예측 날짜 범위 조회

        Args:
            symbol: 심볼

        Returns:
            날짜 범위 정보 (시작일, 종료일)
        """
        result = (
            self.session.query(
                func.min(MLPrediction.prediction_date).label("start_date"),
                func.max(MLPrediction.prediction_date).label("end_date"),
            )
            .filter(MLPrediction.symbol == symbol)
            .first()
        )

        if result and result.start_date and result.end_date:
            return {
                "start_date": result.start_date.isoformat(),
                "end_date": result.end_date.isoformat(),
            }

        return None

    def cleanup_old_predictions(self, days_old: int = 365) -> int:
        """
        오래된 예측 결과 정리

        Args:
            days_old: 며칠 이전 데이터를 삭제할지

        Returns:
            삭제된 레코드 수
        """
        cutoff_date = date.today() - timedelta(days=days_old)

        try:
            deleted_count = (
                self.session.query(MLPrediction)
                .filter(MLPrediction.prediction_date < cutoff_date)
                .delete()
            )

            self.session.commit()

            logger.info(
                "ml_predictions_cleaned_up",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date,
            )

            return deleted_count

        except Exception as e:
            self.session.rollback()
            logger.error("ml_predictions_cleanup_failed", error=str(e))
            return 0

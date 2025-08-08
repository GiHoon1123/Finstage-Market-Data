"""
예측 결과 추적 서비스

이 파일은 ML 예측 결과의 추적, 업데이트, 분석을 담당하는 서비스입니다.
실제 결과와 예측 결과를 비교하여 모델 성능을 지속적으로 모니터링합니다.

주요 기능:
- 예측 결과 실시간 추적
- 실제 결과와의 비교 및 정확도 계산
- 예측 성능 분석 및 리포팅
- 자동 업데이트 스케줄링
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import asyncio
import pandas as pd
from sqlalchemy.orm import Session

from app.ml_prediction.infra.model.repository.ml_prediction_repository import (
    MLPredictionRepository,
)
from app.ml_prediction.infra.model.repository.ml_model_repository import (
    MLModelRepository,
)
from app.technical_analysis.infra.model.repository.daily_price_repository import (
    DailyPriceRepository,
)
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class PredictionTracker:
    """
    예측 결과 추적기

    예측 결과의 정확도를 추적하고 실제 결과와 비교하여
    모델 성능을 지속적으로 모니터링합니다.
    """

    def __init__(self):
        """추적기 초기화"""
        self.update_stats = {
            "last_update": None,
            "total_updated": 0,
            "update_errors": 0,
        }

        logger.info("prediction_tracker_initialized")

    async def update_prediction_results(
        self, days_old: int = 1, symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        예측 결과 업데이트

        Args:
            days_old: 며칠 이전까지의 예측을 업데이트할지
            symbols: 특정 심볼들만 업데이트 (None이면 전체)

        Returns:
            업데이트 결과 딕셔너리
        """
        logger.info(
            "prediction_results_update_started", days_old=days_old, symbols=symbols
        )

        session = SessionLocal()
        prediction_repo = MLPredictionRepository(session)
        price_repo = DailyPriceRepository(session)

        try:
            # 업데이트가 필요한 예측들 조회
            pending_predictions = prediction_repo.find_pending_updates(days_old)

            if symbols:
                # 특정 심볼들만 필터링
                pending_predictions = [
                    pred for pred in pending_predictions if pred.symbol in symbols
                ]

            logger.info("pending_predictions_found", count=len(pending_predictions))

            updated_count = 0
            error_count = 0
            symbol_stats = {}

            for prediction in pending_predictions:
                try:
                    # 실제 가격 데이터 조회
                    actual_prices = price_repo.find_by_symbol_and_date_range(
                        symbol=prediction.symbol,
                        start_date=prediction.target_date,
                        end_date=prediction.target_date,
                        order_desc=False,
                    )

                    if actual_prices:
                        actual_price = float(actual_prices[0].close_price)

                        # 예측 결과 업데이트
                        success = prediction_repo.update_actual_result(
                            prediction.id, actual_price
                        )

                        if success:
                            updated_count += 1

                            # 심볼별 통계 업데이트
                            if prediction.symbol not in symbol_stats:
                                symbol_stats[prediction.symbol] = {
                                    "updated": 0,
                                    "timeframes": {},
                                }

                            symbol_stats[prediction.symbol]["updated"] += 1

                            timeframe = prediction.prediction_timeframe
                            if (
                                timeframe
                                not in symbol_stats[prediction.symbol]["timeframes"]
                            ):
                                symbol_stats[prediction.symbol]["timeframes"][
                                    timeframe
                                ] = 0
                            symbol_stats[prediction.symbol]["timeframes"][
                                timeframe
                            ] += 1

                            logger.debug(
                                "prediction_result_updated",
                                prediction_id=prediction.id,
                                symbol=prediction.symbol,
                                timeframe=prediction.prediction_timeframe,
                                predicted_price=prediction.predicted_price,
                                actual_price=actual_price,
                            )
                        else:
                            error_count += 1
                            logger.warning(
                                "prediction_update_failed",
                                prediction_id=prediction.id,
                                symbol=prediction.symbol,
                            )
                    else:
                        logger.debug(
                            "actual_price_not_available",
                            prediction_id=prediction.id,
                            symbol=prediction.symbol,
                            target_date=prediction.target_date,
                        )

                except Exception as e:
                    error_count += 1
                    logger.error(
                        "prediction_update_error",
                        prediction_id=prediction.id,
                        symbol=prediction.symbol,
                        error=str(e),
                    )

            # 업데이트 통계 갱신
            self.update_stats.update(
                {
                    "last_update": datetime.now(),
                    "total_updated": self.update_stats["total_updated"] + updated_count,
                    "update_errors": self.update_stats["update_errors"] + error_count,
                }
            )

            result = {
                "pending_predictions": len(pending_predictions),
                "updated_count": updated_count,
                "error_count": error_count,
                "symbol_stats": symbol_stats,
                "update_timestamp": datetime.now().isoformat(),
            }

            logger.info(
                "prediction_results_update_completed",
                pending_predictions=len(pending_predictions),
                updated_count=updated_count,
                error_count=error_count,
            )

            return result

        except Exception as e:
            logger.error("prediction_results_update_failed", error=str(e))
            raise
        finally:
            session.close()

    def get_prediction_accuracy_report(
        self, symbol: str, days: int = 30, timeframe: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        예측 정확도 리포트 생성

        Args:
            symbol: 심볼
            days: 분석 기간 (일)
            timeframe: 특정 타임프레임 (선택사항)

        Returns:
            정확도 리포트 딕셔너리
        """
        logger.info(
            "generating_prediction_accuracy_report",
            symbol=symbol,
            days=days,
            timeframe=timeframe,
        )

        session = SessionLocal()
        prediction_repo = MLPredictionRepository(session)

        try:
            # 정확도 지표 조회
            if timeframe:
                accuracy_metrics = prediction_repo.get_accuracy_metrics(
                    symbol, timeframe, days
                )
                timeframe_metrics = {timeframe: accuracy_metrics}
            else:
                timeframe_metrics = prediction_repo.get_performance_by_timeframe(
                    symbol, days
                )

            # 일별 성능 트렌드 조회
            daily_trends = {}
            for tf in ["7d", "14d", "30d"]:
                if not timeframe or timeframe == tf:
                    daily_trends[tf] = prediction_repo.get_daily_performance_trend(
                        symbol, tf, days
                    )

            # 모델 버전별 성능 비교
            model_comparison = prediction_repo.get_model_performance_comparison(
                symbol, days
            )

            # 종합 분석
            overall_stats = self._calculate_overall_stats(timeframe_metrics)

            report = {
                "symbol": symbol,
                "analysis_period_days": days,
                "timeframe_filter": timeframe,
                "generated_at": datetime.now().isoformat(),
                "timeframe_metrics": timeframe_metrics,
                "daily_trends": daily_trends,
                "model_comparison": model_comparison,
                "overall_stats": overall_stats,
                "recommendations": self._generate_recommendations(
                    timeframe_metrics, overall_stats
                ),
            }

            logger.info(
                "prediction_accuracy_report_generated",
                symbol=symbol,
                timeframes=len(timeframe_metrics),
                overall_accuracy=overall_stats.get("avg_direction_accuracy", 0),
            )

            return report

        except Exception as e:
            logger.error(
                "prediction_accuracy_report_failed", symbol=symbol, error=str(e)
            )
            raise
        finally:
            session.close()

    def get_prediction_history(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        include_pending: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        예측 이력 조회

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            include_pending: 미완료 예측 포함 여부

        Returns:
            예측 이력 목록
        """
        logger.info(
            "retrieving_prediction_history",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            include_pending=include_pending,
        )

        session = SessionLocal()
        prediction_repo = MLPredictionRepository(session)

        try:
            # 예측 결과 조회
            predictions = prediction_repo.find_by_symbol_and_date_range(
                symbol=symbol, start_date=start_date, end_date=end_date, order_desc=True
            )

            # 배치별로 그룹화
            batch_groups = {}
            for pred in predictions:
                # 미완료 예측 필터링
                if not include_pending and pred.actual_price is None:
                    continue

                batch_id = pred.batch_id
                if batch_id not in batch_groups:
                    batch_groups[batch_id] = {
                        "batch_id": batch_id,
                        "symbol": pred.symbol,
                        "prediction_date": pred.prediction_date,
                        "model_version": pred.model_version,
                        "predictions": [],
                        "is_complete": True,
                    }

                pred_dict = pred.to_dict()
                batch_groups[batch_id]["predictions"].append(pred_dict)

                # 완료 여부 확인
                if pred.actual_price is None:
                    batch_groups[batch_id]["is_complete"] = False

            # 배치별 통계 계산
            history = []
            for batch_data in batch_groups.values():
                if batch_data["predictions"]:
                    # 배치 통계 계산
                    batch_stats = self._calculate_batch_stats(batch_data["predictions"])
                    batch_data.update(batch_stats)

                    history.append(batch_data)

            # 날짜순 정렬
            history.sort(key=lambda x: x["prediction_date"], reverse=True)

            logger.info(
                "prediction_history_retrieved",
                symbol=symbol,
                batches=len(history),
                total_predictions=sum(len(batch["predictions"]) for batch in history),
            )

            return history

        except Exception as e:
            logger.error(
                "prediction_history_retrieval_failed", symbol=symbol, error=str(e)
            )
            raise
        finally:
            session.close()

    def analyze_prediction_patterns(
        self, symbol: str, days: int = 90
    ) -> Dict[str, Any]:
        """
        예측 패턴 분석

        Args:
            symbol: 심볼
            days: 분석 기간 (일)

        Returns:
            패턴 분석 결과
        """
        logger.info("analyzing_prediction_patterns", symbol=symbol, days=days)

        session = SessionLocal()
        prediction_repo = MLPredictionRepository(session)

        try:
            # 최근 예측 데이터 조회
            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            predictions = prediction_repo.find_by_symbol_and_date_range(
                symbol=symbol, start_date=start_date, end_date=end_date
            )

            # 실제 결과가 있는 예측만 필터링
            completed_predictions = [
                pred for pred in predictions if pred.actual_price is not None
            ]

            if not completed_predictions:
                return {
                    "symbol": symbol,
                    "analysis_period_days": days,
                    "message": "No completed predictions found for analysis",
                    "patterns": {},
                }

            # 패턴 분석
            patterns = {
                "accuracy_by_timeframe": self._analyze_timeframe_accuracy(
                    completed_predictions
                ),
                "accuracy_by_direction": self._analyze_direction_accuracy(
                    completed_predictions
                ),
                "accuracy_by_confidence": self._analyze_confidence_accuracy(
                    completed_predictions
                ),
                "error_distribution": self._analyze_error_distribution(
                    completed_predictions
                ),
                "temporal_patterns": self._analyze_temporal_patterns(
                    completed_predictions
                ),
            }

            # 인사이트 생성
            insights = self._generate_pattern_insights(patterns)

            result = {
                "symbol": symbol,
                "analysis_period_days": days,
                "analyzed_predictions": len(completed_predictions),
                "analysis_date": datetime.now().isoformat(),
                "patterns": patterns,
                "insights": insights,
            }

            logger.info(
                "prediction_patterns_analyzed",
                symbol=symbol,
                analyzed_predictions=len(completed_predictions),
                insights_count=len(insights),
            )

            return result

        except Exception as e:
            logger.error(
                "prediction_pattern_analysis_failed", symbol=symbol, error=str(e)
            )
            raise
        finally:
            session.close()

    def _calculate_overall_stats(
        self, timeframe_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """전체 통계 계산"""
        if not timeframe_metrics:
            return {}

        # 각 지표의 평균 계산
        all_metrics = list(timeframe_metrics.values())

        avg_direction_accuracy = sum(
            m.get("direction_accuracy", 0) for m in all_metrics
        ) / len(all_metrics)

        avg_price_error = sum(
            m.get("avg_price_error_percent", 0) for m in all_metrics
        ) / len(all_metrics)

        avg_confidence = sum(
            m.get("avg_confidence_score", 0) for m in all_metrics
        ) / len(all_metrics)

        avg_quality = sum(m.get("avg_quality_score", 0) for m in all_metrics) / len(
            all_metrics
        )

        return {
            "avg_direction_accuracy": avg_direction_accuracy,
            "avg_price_error_percent": avg_price_error,
            "avg_confidence_score": avg_confidence,
            "avg_quality_score": avg_quality,
            "timeframes_analyzed": len(timeframe_metrics),
        }

    def _generate_recommendations(
        self,
        timeframe_metrics: Dict[str, Dict[str, float]],
        overall_stats: Dict[str, float],
    ) -> List[str]:
        """추천사항 생성"""
        recommendations = []

        # 전체 정확도 기반 추천
        avg_accuracy = overall_stats.get("avg_direction_accuracy", 0)
        if avg_accuracy < 0.5:
            recommendations.append("모델 성능이 낮습니다. 재훈련을 고려해보세요.")
        elif avg_accuracy > 0.7:
            recommendations.append("모델 성능이 우수합니다. 현재 모델을 유지하세요.")

        # 타임프레임별 성능 비교
        if len(timeframe_metrics) > 1:
            accuracies = {
                tf: metrics.get("direction_accuracy", 0)
                for tf, metrics in timeframe_metrics.items()
            }

            best_timeframe = max(accuracies, key=accuracies.get)
            worst_timeframe = min(accuracies, key=accuracies.get)

            if accuracies[best_timeframe] - accuracies[worst_timeframe] > 0.2:
                recommendations.append(
                    f"{best_timeframe} 예측이 가장 정확합니다. "
                    f"{worst_timeframe} 예측 개선이 필요합니다."
                )

        # 신뢰도 기반 추천
        avg_confidence = overall_stats.get("avg_confidence_score", 0)
        if avg_confidence < 0.6:
            recommendations.append(
                "예측 신뢰도가 낮습니다. 모델 복잡도를 높이거나 더 많은 데이터로 훈련하세요."
            )

        return recommendations

    def _calculate_batch_stats(
        self, predictions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """배치 통계 계산"""
        completed_preds = [
            pred for pred in predictions if pred["actual"]["actual_price"] is not None
        ]

        if not completed_preds:
            return {"completion_rate": 0.0, "avg_accuracy": 0.0, "avg_confidence": 0.0}

        completion_rate = len(completed_preds) / len(predictions)

        correct_directions = sum(
            1 for pred in completed_preds if pred["actual"]["is_direction_correct"]
        )
        avg_accuracy = (
            correct_directions / len(completed_preds) if completed_preds else 0
        )

        avg_confidence = sum(
            pred["prediction"]["confidence_score"] for pred in completed_preds
        ) / len(completed_preds)

        return {
            "completion_rate": completion_rate,
            "avg_accuracy": avg_accuracy,
            "avg_confidence": avg_confidence,
            "completed_predictions": len(completed_preds),
            "total_predictions": len(predictions),
        }

    def _analyze_timeframe_accuracy(self, predictions) -> Dict[str, float]:
        """타임프레임별 정확도 분석"""
        timeframe_stats = {}

        for pred in predictions:
            tf = pred.prediction_timeframe
            if tf not in timeframe_stats:
                timeframe_stats[tf] = {"correct": 0, "total": 0}

            timeframe_stats[tf]["total"] += 1
            if pred.is_direction_correct:
                timeframe_stats[tf]["correct"] += 1

        return {
            tf: stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            for tf, stats in timeframe_stats.items()
        }

    def _analyze_direction_accuracy(self, predictions) -> Dict[str, float]:
        """방향별 정확도 분석"""
        direction_stats = {}

        for pred in predictions:
            direction = pred.predicted_direction
            if direction not in direction_stats:
                direction_stats[direction] = {"correct": 0, "total": 0}

            direction_stats[direction]["total"] += 1
            if pred.is_direction_correct:
                direction_stats[direction]["correct"] += 1

        return {
            direction: stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            for direction, stats in direction_stats.items()
        }

    def _analyze_confidence_accuracy(self, predictions) -> Dict[str, Any]:
        """신뢰도별 정확도 분석"""
        # 신뢰도를 구간별로 나누어 분석
        confidence_ranges = [
            (0.0, 0.5, "low"),
            (0.5, 0.7, "medium"),
            (0.7, 1.0, "high"),
        ]

        range_stats = {}

        for min_conf, max_conf, label in confidence_ranges:
            range_preds = [
                pred
                for pred in predictions
                if min_conf <= float(pred.confidence_score) < max_conf
            ]

            if range_preds:
                correct = sum(1 for pred in range_preds if pred.is_direction_correct)
                accuracy = correct / len(range_preds)

                range_stats[label] = {
                    "accuracy": accuracy,
                    "count": len(range_preds),
                    "confidence_range": f"{min_conf}-{max_conf}",
                }

        return range_stats

    def _analyze_error_distribution(self, predictions) -> Dict[str, Any]:
        """오차 분포 분석"""
        errors = [
            float(pred.price_error_percent)
            for pred in predictions
            if pred.price_error_percent is not None
        ]

        if not errors:
            return {}

        import numpy as np

        return {
            "mean_error": float(np.mean(errors)),
            "median_error": float(np.median(errors)),
            "std_error": float(np.std(errors)),
            "min_error": float(np.min(errors)),
            "max_error": float(np.max(errors)),
            "percentiles": {
                "25th": float(np.percentile(errors, 25)),
                "75th": float(np.percentile(errors, 75)),
                "90th": float(np.percentile(errors, 90)),
            },
        }

    def _analyze_temporal_patterns(self, predictions) -> Dict[str, Any]:
        """시간적 패턴 분석"""
        # 요일별 성능
        weekday_stats = {}
        for pred in predictions:
            weekday = pred.prediction_date.weekday()  # 0=월요일
            if weekday not in weekday_stats:
                weekday_stats[weekday] = {"correct": 0, "total": 0}

            weekday_stats[weekday]["total"] += 1
            if pred.is_direction_correct:
                weekday_stats[weekday]["correct"] += 1

        weekday_accuracy = {
            f"weekday_{day}": (
                stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            )
            for day, stats in weekday_stats.items()
        }

        return {"weekday_accuracy": weekday_accuracy}

    def _generate_pattern_insights(self, patterns: Dict[str, Any]) -> List[str]:
        """패턴 기반 인사이트 생성"""
        insights = []

        # 타임프레임 성능 인사이트
        tf_accuracy = patterns.get("accuracy_by_timeframe", {})
        if tf_accuracy:
            best_tf = max(tf_accuracy, key=tf_accuracy.get)
            worst_tf = min(tf_accuracy, key=tf_accuracy.get)

            insights.append(
                f"{best_tf} 예측이 가장 정확합니다 ({tf_accuracy[best_tf]:.2%})"
            )

            if tf_accuracy[best_tf] - tf_accuracy[worst_tf] > 0.15:
                insights.append(
                    f"{worst_tf} 예측 성능이 상대적으로 낮습니다 ({tf_accuracy[worst_tf]:.2%})"
                )

        # 신뢰도 인사이트
        conf_accuracy = patterns.get("accuracy_by_confidence", {})
        if "high" in conf_accuracy and "low" in conf_accuracy:
            high_acc = conf_accuracy["high"]["accuracy"]
            low_acc = conf_accuracy["low"]["accuracy"]

            if high_acc > low_acc + 0.1:
                insights.append("높은 신뢰도 예측이 실제로 더 정확합니다")
            else:
                insights.append("신뢰도와 실제 정확도 간의 상관관계가 약합니다")

        return insights

    def get_tracker_stats(self) -> Dict[str, Any]:
        """추적기 통계 반환"""
        return {
            "update_stats": self.update_stats,
            "last_update_time": (
                self.update_stats["last_update"].isoformat()
                if self.update_stats["last_update"]
                else None
            ),
        }

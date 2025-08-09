"""
모델 평가기

이 파일은 ML 모델의 성능을 종합적으로 평가하는 클래스를 구현합니다.
다양한 평가 지표를 계산하고 모델 성능을 분석합니다.

주요 기능:
- 멀티 타임프레임 성능 평가
- 다양한 평가 지표 계산
- 성능 비교 및 분석
- 평가 리포트 생성
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd

try:
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    SKLEARN_AVAILABLE = True
except ImportError:
    mean_squared_error = None
    mean_absolute_error = None
    r2_score = None
    SKLEARN_AVAILABLE = False
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

from app.ml_prediction.ml.model.lstm_model import MultiOutputLSTMPredictor
from app.ml_prediction.infra.model.repository.ml_prediction_repository import (
    MLPredictionRepository,
)
from app.ml_prediction.infra.model.repository.ml_model_repository import (
    MLModelRepository,
)
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class ModelEvaluator:
    """
    모델 평가기

    ML 모델의 성능을 다양한 지표로 평가하고 분석합니다.
    """

    def __init__(self):
        """평가기 초기화"""
        self.evaluation_cache = {}

        logger.info("model_evaluator_initialized")

    def evaluate_model_performance(
        self,
        symbol: str,
        model_version: Optional[str] = None,
        evaluation_days: int = 90,
        include_visualizations: bool = False,
    ) -> Dict[str, Any]:
        """
        모델 성능 종합 평가

        Args:
            symbol: 심볼
            model_version: 모델 버전 (None이면 활성 모델)
            evaluation_days: 평가 기간 (일)
            include_visualizations: 시각화 포함 여부

        Returns:
            종합 평가 결과
        """
        logger.info(
            "model_performance_evaluation_started",
            symbol=symbol,
            model_version=model_version,
            evaluation_days=evaluation_days,
        )

        session = SessionLocal()
        prediction_repo = MLPredictionRepository(session)
        model_repo = MLModelRepository(session)

        try:
            # 모델 정보 조회
            if model_version:
                model_name = f"{symbol.replace('^', '')}_lstm"
                model_entity = model_repo.find_by_name_and_version(
                    model_name, model_version
                )
            else:
                model_entity = model_repo.find_active_model("lstm", symbol)

            if not model_entity:
                raise ValueError(f"Model not found for {symbol}")

            # 평가 데이터 조회
            end_date = date.today()
            start_date = end_date - timedelta(days=evaluation_days)

            predictions = prediction_repo.find_by_model_version(
                model_entity.model_version, symbol
            )

            # 실제 결과가 있는 예측만 필터링
            completed_predictions = [
                pred
                for pred in predictions
                if pred.actual_price is not None and pred.prediction_date >= start_date
            ]

            if not completed_predictions:
                return {
                    "symbol": symbol,
                    "model_version": model_entity.model_version,
                    "evaluation_period": evaluation_days,
                    "message": "No completed predictions found for evaluation",
                    "metrics": {},
                }

            # 타임프레임별 평가
            timeframe_metrics = {}
            for timeframe in ["7d", "14d", "30d"]:
                tf_predictions = [
                    pred
                    for pred in completed_predictions
                    if pred.prediction_timeframe == timeframe
                ]

                if tf_predictions:
                    metrics = self._calculate_comprehensive_metrics(tf_predictions)
                    timeframe_metrics[timeframe] = metrics

            # 전체 성능 지표
            overall_metrics = self._calculate_overall_metrics(timeframe_metrics)

            # 성능 트렌드 분석
            performance_trends = self._analyze_performance_trends(completed_predictions)

            # 오차 분석
            error_analysis = self._analyze_prediction_errors(completed_predictions)

            # 신뢰도 분석
            confidence_analysis = self._analyze_confidence_calibration(
                completed_predictions
            )

            # 시각화 생성
            visualizations = {}
            if include_visualizations:
                visualizations = self._generate_evaluation_visualizations(
                    completed_predictions, timeframe_metrics
                )

            # 평가 결과 구성
            evaluation_result = {
                "symbol": symbol,
                "model_info": {
                    "model_id": model_entity.id,
                    "model_name": model_entity.model_name,
                    "model_version": model_entity.model_version,
                    "model_type": model_entity.model_type,
                    "training_date": (
                        model_entity.training_end_date.isoformat()
                        if model_entity.training_end_date
                        else None
                    ),
                },
                "evaluation_period": {
                    "days": evaluation_days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_predictions": len(completed_predictions),
                },
                "timeframe_metrics": timeframe_metrics,
                "overall_metrics": overall_metrics,
                "performance_trends": performance_trends,
                "error_analysis": error_analysis,
                "confidence_analysis": confidence_analysis,
                "visualizations": visualizations,
                "evaluation_timestamp": datetime.now().isoformat(),
            }

            # 캐시에 저장
            cache_key = f"{symbol}_{model_entity.model_version}_{evaluation_days}"
            self.evaluation_cache[cache_key] = evaluation_result

            logger.info(
                "model_performance_evaluation_completed",
                symbol=symbol,
                model_version=model_entity.model_version,
                total_predictions=len(completed_predictions),
                overall_accuracy=overall_metrics.get("avg_direction_accuracy", 0),
            )

            return evaluation_result

        except Exception as e:
            logger.error(
                "model_performance_evaluation_failed", symbol=symbol, error=str(e)
            )
            raise
        finally:
            session.close()

    def compare_models(
        self, symbol: str, model_versions: List[str], evaluation_days: int = 90
    ) -> Dict[str, Any]:
        """
        여러 모델 성능 비교

        Args:
            symbol: 심볼
            model_versions: 비교할 모델 버전 목록
            evaluation_days: 평가 기간

        Returns:
            모델 비교 결과
        """
        logger.info(
            "model_comparison_started",
            symbol=symbol,
            model_versions=model_versions,
            evaluation_days=evaluation_days,
        )

        model_evaluations = {}

        # 각 모델 평가
        for version in model_versions:
            try:
                evaluation = self.evaluate_model_performance(
                    symbol=symbol,
                    model_version=version,
                    evaluation_days=evaluation_days,
                    include_visualizations=False,
                )
                model_evaluations[version] = evaluation

            except Exception as e:
                logger.warning(
                    "model_evaluation_failed_in_comparison",
                    symbol=symbol,
                    model_version=version,
                    error=str(e),
                )
                model_evaluations[version] = {"error": str(e)}

        # 성공한 평가만 비교
        valid_evaluations = {
            version: eval_data
            for version, eval_data in model_evaluations.items()
            if "error" not in eval_data
        }

        if len(valid_evaluations) < 2:
            return {
                "symbol": symbol,
                "comparison_date": datetime.now().isoformat(),
                "message": "Need at least 2 valid model evaluations for comparison",
                "model_evaluations": model_evaluations,
            }

        # 비교 분석
        comparison_analysis = self._perform_model_comparison(valid_evaluations)

        result = {
            "symbol": symbol,
            "evaluation_period_days": evaluation_days,
            "compared_models": len(valid_evaluations),
            "comparison_date": datetime.now().isoformat(),
            "model_evaluations": model_evaluations,
            "comparison_analysis": comparison_analysis,
        }

        logger.info(
            "model_comparison_completed",
            symbol=symbol,
            compared_models=len(valid_evaluations),
            best_model=comparison_analysis.get("best_overall_model"),
        )

        return result

    def _calculate_comprehensive_metrics(self, predictions) -> Dict[str, float]:
        """종합 평가 지표 계산"""
        if not predictions:
            return {}

        # 기본 데이터 추출
        y_true = np.array([float(pred.actual_price) for pred in predictions])
        y_pred = np.array([float(pred.predicted_price) for pred in predictions])

        # 방향성 정확도
        direction_correct = sum(1 for pred in predictions if pred.is_direction_correct)
        direction_accuracy = direction_correct / len(predictions)

        # 회귀 지표
        mse = mean_squared_error(y_true, y_pred)
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mse)

        # R² 점수
        r2 = r2_score(y_true, y_pred)

        # 평균 절대 백분율 오차 (MAPE)
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

        # 신뢰도 관련 지표
        confidence_scores = [float(pred.confidence_score) for pred in predictions]
        avg_confidence = np.mean(confidence_scores)

        # 수익률 기반 지표
        returns_metrics = self._calculate_returns_metrics(predictions)

        return {
            "direction_accuracy": direction_accuracy,
            "mse": mse,
            "mae": mae,
            "rmse": rmse,
            "r2_score": r2,
            "mape": mape,
            "avg_confidence": avg_confidence,
            "total_predictions": len(predictions),
            **returns_metrics,
        }

    def _calculate_returns_metrics(self, predictions) -> Dict[str, float]:
        """수익률 기반 지표 계산"""
        returns_data = []

        for pred in predictions:
            current_price = float(pred.current_price)
            predicted_price = float(pred.predicted_price)
            actual_price = float(pred.actual_price)

            predicted_return = (predicted_price - current_price) / current_price
            actual_return = (actual_price - current_price) / current_price

            returns_data.append(
                {"predicted_return": predicted_return, "actual_return": actual_return}
            )

        if not returns_data:
            return {}

        pred_returns = np.array([r["predicted_return"] for r in returns_data])
        actual_returns = np.array([r["actual_return"] for r in returns_data])

        # 수익률 상관관계
        return_correlation = np.corrcoef(pred_returns, actual_returns)[0, 1]

        # 수익률 MSE
        return_mse = mean_squared_error(actual_returns, pred_returns)

        return {
            "return_correlation": (
                return_correlation if not np.isnan(return_correlation) else 0.0
            ),
            "return_mse": return_mse,
            "avg_predicted_return": float(np.mean(pred_returns)),
            "avg_actual_return": float(np.mean(actual_returns)),
        }

    def _calculate_overall_metrics(
        self, timeframe_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """전체 성능 지표 계산"""
        if not timeframe_metrics:
            return {}

        # 각 지표의 가중 평균 계산 (7d: 50%, 14d: 30%, 30d: 20%)
        weights = {"7d": 0.5, "14d": 0.3, "30d": 0.2}

        metrics_to_average = [
            "direction_accuracy",
            "mse",
            "mae",
            "rmse",
            "r2_score",
            "mape",
            "avg_confidence",
            "return_correlation",
        ]

        overall_metrics = {}

        for metric in metrics_to_average:
            weighted_sum = 0
            total_weight = 0

            for timeframe, metrics in timeframe_metrics.items():
                if metric in metrics and timeframe in weights:
                    weighted_sum += metrics[metric] * weights[timeframe]
                    total_weight += weights[timeframe]

            if total_weight > 0:
                overall_metrics[f"avg_{metric}"] = weighted_sum / total_weight

        # 총 예측 수
        overall_metrics["total_predictions"] = sum(
            metrics.get("total_predictions", 0)
            for metrics in timeframe_metrics.values()
        )

        # 성능 등급 계산
        overall_metrics["performance_grade"] = self._calculate_performance_grade(
            overall_metrics
        )

        return overall_metrics

    def _calculate_performance_grade(self, metrics: Dict[str, float]) -> str:
        """성능 등급 계산"""
        direction_accuracy = metrics.get("avg_direction_accuracy", 0)
        r2_score = metrics.get("avg_r2_score", 0)

        # 방향 정확도와 R² 점수를 기반으로 등급 결정
        if direction_accuracy >= 0.7 and r2_score >= 0.3:
            return "A"
        elif direction_accuracy >= 0.6 and r2_score >= 0.2:
            return "B"
        elif direction_accuracy >= 0.5 and r2_score >= 0.1:
            return "C"
        else:
            return "D"

    def _analyze_performance_trends(self, predictions) -> Dict[str, Any]:
        """성능 트렌드 분석"""
        # 날짜별로 정렬
        sorted_predictions = sorted(predictions, key=lambda x: x.prediction_date)

        # 주간별 성능 계산
        weekly_performance = []
        current_week = []
        current_week_start = None

        for pred in sorted_predictions:
            if current_week_start is None:
                current_week_start = pred.prediction_date
                current_week = [pred]
            elif (pred.prediction_date - current_week_start).days < 7:
                current_week.append(pred)
            else:
                # 주간 성능 계산
                if current_week:
                    week_accuracy = sum(
                        1 for p in current_week if p.is_direction_correct
                    ) / len(current_week)
                    weekly_performance.append(
                        {
                            "week_start": current_week_start.isoformat(),
                            "predictions_count": len(current_week),
                            "accuracy": week_accuracy,
                        }
                    )

                current_week_start = pred.prediction_date
                current_week = [pred]

        # 마지막 주 처리
        if current_week:
            week_accuracy = sum(
                1 for p in current_week if p.is_direction_correct
            ) / len(current_week)
            weekly_performance.append(
                {
                    "week_start": current_week_start.isoformat(),
                    "predictions_count": len(current_week),
                    "accuracy": week_accuracy,
                }
            )

        # 트렌드 분석
        if len(weekly_performance) >= 2:
            recent_accuracy = np.mean([w["accuracy"] for w in weekly_performance[-2:]])
            early_accuracy = np.mean([w["accuracy"] for w in weekly_performance[:2]])
            trend = "improving" if recent_accuracy > early_accuracy else "declining"
        else:
            trend = "insufficient_data"

        return {
            "weekly_performance": weekly_performance,
            "trend": trend,
            "weeks_analyzed": len(weekly_performance),
        }

    def _analyze_prediction_errors(self, predictions) -> Dict[str, Any]:
        """예측 오차 분석"""
        errors = []

        for pred in predictions:
            if pred.price_error_percent is not None:
                errors.append(
                    {
                        "error_percent": float(pred.price_error_percent),
                        "timeframe": pred.prediction_timeframe,
                        "confidence": float(pred.confidence_score),
                        "predicted_direction": pred.predicted_direction,
                    }
                )

        if not errors:
            return {}

        error_values = [e["error_percent"] for e in errors]

        # 기본 통계
        error_stats = {
            "mean_error": float(np.mean(error_values)),
            "median_error": float(np.median(error_values)),
            "std_error": float(np.std(error_values)),
            "min_error": float(np.min(error_values)),
            "max_error": float(np.max(error_values)),
        }

        # 타임프레임별 오차
        timeframe_errors = {}
        for tf in ["7d", "14d", "30d"]:
            tf_errors = [e["error_percent"] for e in errors if e["timeframe"] == tf]
            if tf_errors:
                timeframe_errors[tf] = {
                    "mean_error": float(np.mean(tf_errors)),
                    "count": len(tf_errors),
                }

        # 방향별 오차
        direction_errors = {}
        for direction in ["up", "down", "neutral"]:
            dir_errors = [
                e["error_percent"]
                for e in errors
                if e["predicted_direction"] == direction
            ]
            if dir_errors:
                direction_errors[direction] = {
                    "mean_error": float(np.mean(dir_errors)),
                    "count": len(dir_errors),
                }

        return {
            "overall_stats": error_stats,
            "timeframe_errors": timeframe_errors,
            "direction_errors": direction_errors,
            "total_analyzed": len(errors),
        }

    def _analyze_confidence_calibration(self, predictions) -> Dict[str, Any]:
        """신뢰도 보정 분석"""
        confidence_bins = []

        # 신뢰도를 10개 구간으로 나누어 분석
        for i in range(10):
            bin_min = i * 0.1
            bin_max = (i + 1) * 0.1

            bin_predictions = [
                pred
                for pred in predictions
                if bin_min <= float(pred.confidence_score) < bin_max
            ]

            if bin_predictions:
                accuracy = sum(
                    1 for pred in bin_predictions if pred.is_direction_correct
                ) / len(bin_predictions)
                avg_confidence = np.mean(
                    [float(pred.confidence_score) for pred in bin_predictions]
                )

                confidence_bins.append(
                    {
                        "confidence_range": f"{bin_min:.1f}-{bin_max:.1f}",
                        "avg_confidence": avg_confidence,
                        "accuracy": accuracy,
                        "count": len(bin_predictions),
                        "calibration_error": abs(avg_confidence - accuracy),
                    }
                )

        # 전체 보정 오차 계산
        if confidence_bins:
            total_calibration_error = np.mean(
                [bin_data["calibration_error"] for bin_data in confidence_bins]
            )
        else:
            total_calibration_error = 0.0

        return {
            "confidence_bins": confidence_bins,
            "overall_calibration_error": total_calibration_error,
            "bins_analyzed": len(confidence_bins),
        }

    def _generate_evaluation_visualizations(
        self, predictions, timeframe_metrics: Dict[str, Dict[str, float]]
    ) -> Dict[str, str]:
        """평가 시각화 생성"""
        visualizations = {}

        try:
            # 1. 타임프레임별 정확도 비교
            if timeframe_metrics:
                fig, ax = plt.subplots(figsize=(10, 6))

                timeframes = list(timeframe_metrics.keys())
                accuracies = [
                    metrics.get("direction_accuracy", 0)
                    for metrics in timeframe_metrics.values()
                ]

                bars = ax.bar(
                    timeframes, accuracies, color=["#1f77b4", "#ff7f0e", "#2ca02c"]
                )
                ax.set_ylabel("Direction Accuracy")
                ax.set_title("Prediction Accuracy by Timeframe")
                ax.set_ylim(0, 1)

                # 값 표시
                for bar, acc in zip(bars, accuracies):
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + 0.01,
                        f"{acc:.2%}",
                        ha="center",
                        va="bottom",
                    )

                # Base64로 인코딩
                buffer = BytesIO()
                plt.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
                buffer.seek(0)
                visualizations["timeframe_accuracy"] = base64.b64encode(
                    buffer.getvalue()
                ).decode()
                plt.close()

            # 2. 오차 분포 히스토그램
            errors = [
                float(pred.price_error_percent)
                for pred in predictions
                if pred.price_error_percent is not None
            ]
            if errors:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.hist(errors, bins=20, alpha=0.7, color="skyblue", edgecolor="black")
                ax.set_xlabel("Price Error (%)")
                ax.set_ylabel("Frequency")
                ax.set_title("Distribution of Prediction Errors")
                ax.axvline(
                    np.mean(errors),
                    color="red",
                    linestyle="--",
                    label=f"Mean: {np.mean(errors):.2f}%",
                )
                ax.legend()

                buffer = BytesIO()
                plt.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
                buffer.seek(0)
                visualizations["error_distribution"] = base64.b64encode(
                    buffer.getvalue()
                ).decode()
                plt.close()

        except Exception as e:
            logger.warning("visualization_generation_failed", error=str(e))

        return visualizations

    def _perform_model_comparison(
        self, model_evaluations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """모델 비교 분석"""
        comparison_metrics = [
            "avg_direction_accuracy",
            "avg_mse",
            "avg_mae",
            "avg_r2_score",
        ]

        model_scores = {}

        # 각 모델의 종합 점수 계산
        for version, evaluation in model_evaluations.items():
            overall_metrics = evaluation.get("overall_metrics", {})

            # 정규화된 점수 계산 (0-1 범위)
            score = 0
            score += (
                overall_metrics.get("avg_direction_accuracy", 0) * 0.4
            )  # 40% 가중치
            score += max(0, overall_metrics.get("avg_r2_score", 0)) * 0.3  # 30% 가중치
            score += (
                1 - min(1, overall_metrics.get("avg_mape", 100) / 100)
            ) * 0.2  # 20% 가중치
            score += (
                overall_metrics.get("avg_return_correlation", 0) * 0.1
            )  # 10% 가중치

            model_scores[version] = {
                "composite_score": score,
                "performance_grade": overall_metrics.get("performance_grade", "D"),
                "total_predictions": overall_metrics.get("total_predictions", 0),
            }

        # 최고 성능 모델 선정
        best_model = max(
            model_scores.keys(), key=lambda x: model_scores[x]["composite_score"]
        )

        # 성능 차이 분석
        performance_gaps = {}
        best_score = model_scores[best_model]["composite_score"]

        for version, scores in model_scores.items():
            if version != best_model:
                performance_gaps[version] = best_score - scores["composite_score"]

        return {
            "best_overall_model": best_model,
            "model_scores": model_scores,
            "performance_gaps": performance_gaps,
            "comparison_summary": self._generate_comparison_summary(
                model_evaluations, best_model
            ),
        }

    def _generate_comparison_summary(
        self, model_evaluations: Dict[str, Dict[str, Any]], best_model: str
    ) -> List[str]:
        """비교 요약 생성"""
        summary = []

        best_eval = model_evaluations[best_model]
        best_accuracy = best_eval["overall_metrics"].get("avg_direction_accuracy", 0)

        summary.append(f"최고 성능 모델: {best_model} (정확도: {best_accuracy:.2%})")

        # 다른 모델들과 비교
        for version, evaluation in model_evaluations.items():
            if version != best_model:
                accuracy = evaluation["overall_metrics"].get(
                    "avg_direction_accuracy", 0
                )
                diff = best_accuracy - accuracy
                summary.append(f"{version}: 정확도 {accuracy:.2%} (차이: {diff:.2%})")

        return summary

    def get_evaluation_cache_stats(self) -> Dict[str, Any]:
        """평가 캐시 통계 반환"""
        return {
            "cached_evaluations": len(self.evaluation_cache),
            "cache_keys": list(self.evaluation_cache.keys()),
        }

    def clear_evaluation_cache(self) -> None:
        """평가 캐시 초기화"""
        self.evaluation_cache.clear()
        logger.info("evaluation_cache_cleared")

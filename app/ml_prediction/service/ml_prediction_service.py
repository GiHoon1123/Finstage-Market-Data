"""
ML 예측 서비스

이 파일은 ML 예측 시스템의 핵심 비즈니스 로직을 구현합니다.
모델 훈련, 예측 실행, 결과 관리 등의 전체 워크플로우를 제공합니다.

주요 기능:
- 모델 훈련 워크플로우 관리
- 실시간 예측 서비스
- 예측 결과 저장 및 추적
- 모델 성능 모니터링
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

from app.ml_prediction.ml.model.trainer import ModelTrainer
from app.ml_prediction.ml.model.predictor import MultiTimeframePredictor
from app.ml_prediction.ml.evaluation.evaluator import ModelEvaluator
from app.ml_prediction.ml.evaluation.result_tracker import PredictionResultTracker
from app.ml_prediction.ml.evaluation.backtester import Backtester, BacktestConfig
from app.ml_prediction.infra.model.repository.ml_prediction_repository import (
    MLPredictionRepository,
)
from app.ml_prediction.infra.model.repository.ml_model_repository import (
    MLModelRepository,
)
from app.ml_prediction.infra.model.entity.ml_prediction import MLPrediction
from app.ml_prediction.config.ml_config import ml_settings
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MLPredictionService:
    """
    ML 예측 서비스

    ML 예측 시스템의 핵심 비즈니스 로직을 담당합니다.
    """

    # 심볼 매핑 (ML 훈련용 심볼 -> 실제 데이터베이스 심볼)
    SYMBOL_MAPPING = {
        "IXIC": "^IXIC",
        "GSPC": "^GSPC",
        "^IXIC": "^IXIC",  # 이미 올바른 형태인 경우
        "^GSPC": "^GSPC",  # 이미 올바른 형태인 경우
    }

    def __init__(self, config=None):
        """
        서비스 초기화

        Args:
            config: ML 설정
        """
        self.config = config or ml_settings
        self.trainer = ModelTrainer()
        self.predictor = MultiTimeframePredictor()
        self.evaluator = ModelEvaluator()
        self.result_tracker = PredictionResultTracker()

        # 스레드 풀 (비동기 작업용)
        self.executor = ThreadPoolExecutor(max_workers=3)

        logger.info(
            "ml_prediction_service_initialized",
            model_storage_path=self.config.storage.base_model_path,
            supported_timeframes=self.config.model.target_days,
        )

    def _normalize_symbol(self, symbol: str) -> str:
        """
        심볼 정규화 (ML 훈련용 심볼을 실제 데이터베이스 심볼로 변환)
        
        Args:
            symbol: 원본 심볼
            
        Returns:
            정규화된 심볼
        """
        normalized_symbol = self.SYMBOL_MAPPING.get(symbol, symbol)
        logger.info(
            "symbol_normalized", 
            original_symbol=symbol, 
            normalized_symbol=normalized_symbol
        )
        return normalized_symbol

    async def train_model(
        self,
        symbol: str,
        training_days: int = 1000,
        validation_split: float = 0.2,
        force_retrain: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_sentiment: bool = False,
    ) -> Dict[str, Any]:
        """
        모델 훈련

        Args:
            symbol: 심볼
            training_days: 훈련 데이터 일수
            validation_split: 검증 데이터 비율
            force_retrain: 강제 재훈련 여부

        Returns:
            훈련 결과
        """
        # 심볼 정규화
        normalized_symbol = self._normalize_symbol(symbol)
        
        logger.info(
            "model_training_started",
            original_symbol=symbol,
            normalized_symbol=normalized_symbol,
            training_days=training_days,
            validation_split=validation_split,
            force_retrain=force_retrain,
            use_sentiment=use_sentiment,
        )

        try:
            # 기존 모델 확인
            if not force_retrain:
                existing_model = await self._check_existing_model(normalized_symbol)
                if existing_model:
                    logger.info(
                        "existing_model_found",
                        symbol=normalized_symbol,
                        model_version=existing_model["model_version"],
                    )
                    return {
                        "status": "skipped",
                        "message": "Model already exists",
                        "existing_model": existing_model,
                    }

            # 비동기로 훈련 실행
            training_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._train_model_sync,
                normalized_symbol,
                training_days,
                validation_split,
                force_retrain,
                start_date,
                end_date,
                use_sentiment,
            )

            # 훈련 후 초기 평가
            if training_result["status"] == "success":
                evaluation_result = await self.evaluate_model_performance(
                    symbol=normalized_symbol,
                    model_version=training_result["model_version"],
                    evaluation_days=30,
                )
                training_result["initial_evaluation"] = evaluation_result

            logger.info(
                "model_training_completed",
                symbol=normalized_symbol,
                status=training_result["status"],
                model_version=training_result.get("model_version"),
            )

            return training_result

        except Exception as e:
            logger.error("model_training_failed", symbol=normalized_symbol, error=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _train_model_sync(
        self,
        symbol: str,
        training_days: int,
        validation_split: float,
        force_retrain: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_sentiment: bool = False,
    ) -> Dict[str, Any]:
        """동기 모델 훈련 (스레드 풀에서 실행)"""
        from datetime import date, timedelta

        if start_date is None or end_date is None:
            end_date = date.today()
            start_date = end_date - timedelta(days=training_days)

        return self.trainer.train_model(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            force_retrain=force_retrain,
            use_sentiment=use_sentiment,
        )

    async def predict_prices(
        self,
        symbol: str,
        prediction_date: Optional[date] = None,
        model_version: Optional[str] = None,
        save_results: bool = True,
        use_sentiment: bool = False,
    ) -> Dict[str, Any]:
        """
        가격 예측

        Args:
            symbol: 심볼
            prediction_date: 예측 기준 날짜 (기본값: 오늘)
            model_version: 사용할 모델 버전 (기본값: 활성 모델)
            save_results: 결과 저장 여부
            use_sentiment: 감정분석 특성 사용 여부

        Returns:
            예측 결과
        """
        # 심볼 정규화
        normalized_symbol = self._normalize_symbol(symbol)
        prediction_date = prediction_date or date.today()

        logger.info(
            "price_prediction_started",
            original_symbol=symbol,
            normalized_symbol=normalized_symbol,
            prediction_date=prediction_date,
            model_version=model_version,
            save_results=save_results,
            use_sentiment=use_sentiment,
        )

        try:
            # 비동기로 예측 실행
            prediction_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._predict_prices_sync,
                normalized_symbol,
                prediction_date,
                model_version,
                use_sentiment,
            )

            # 결과 저장
            if save_results and prediction_result["status"] == "success":
                await self._save_prediction_results(
                    normalized_symbol, prediction_date, prediction_result
                )

            logger.info(
                "price_prediction_completed",
                symbol=normalized_symbol,
                prediction_date=prediction_date,
                status=prediction_result["status"],
                predictions_count=len(prediction_result.get("predictions", [])),
            )

            return prediction_result

        except Exception as e:
            logger.error(
                "price_prediction_failed",
                symbol=normalized_symbol,
                prediction_date=prediction_date,
                error=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def _predict_prices_sync(
        self, symbol: str, prediction_date: date, model_version: Optional[str], use_sentiment: bool
    ) -> Dict[str, Any]:
        """동기 가격 예측 (스레드 풀에서 실행)"""
        return self.predictor.predict_price(
            symbol=symbol, prediction_date=prediction_date, model_version=model_version, use_sentiment=use_sentiment
        )

    async def _save_prediction_results(
        self, symbol: str, prediction_date: date, prediction_result: Dict[str, Any]
    ) -> None:
        """예측 결과 저장"""
        session = SessionLocal()
        prediction_repo = MLPredictionRepository(session)

        try:
            # 전체 결과에서 공통 정보 추출
            batch_id = prediction_result.get(
                "batch_id",
                f"{symbol}_{prediction_date.strftime('%Y%m%d')}_{datetime.now().strftime('%H%M%S')}",
            )
            model_version = prediction_result.get("model_version", "unknown")
            model_type = prediction_result.get("model_type", "lstm")
            current_price = prediction_result.get("current_price", 0.0)

            for pred in prediction_result.get("predictions", []):
                prediction_entity = MLPrediction(
                    symbol=symbol,
                    prediction_date=prediction_date,
                    target_date=pred["target_date"],
                    prediction_timeframe=pred["timeframe"],
                    predicted_price=pred["predicted_price"],
                    predicted_direction=pred["predicted_direction"],
                    confidence_score=pred["confidence_score"],
                    current_price=current_price,
                    model_version=model_version,
                    model_type=model_type,
                    batch_id=batch_id,
                    created_at=datetime.now(),
                )

                prediction_repo.save(prediction_entity)

            logger.info(
                "prediction_results_saved",
                symbol=symbol,
                prediction_date=prediction_date,
                batch_id=batch_id,
                predictions_count=len(prediction_result.get("predictions", [])),
            )

        except Exception as e:
            logger.error(
                "prediction_results_save_failed",
                symbol=symbol,
                prediction_date=prediction_date,
                error=str(e),
            )
            raise
        finally:
            session.close()

    async def evaluate_model_performance(
        self,
        symbol: str,
        model_version: Optional[str] = None,
        evaluation_days: int = 90,
        include_visualizations: bool = False,
    ) -> Dict[str, Any]:
        """
        모델 성능 평가

        Args:
            symbol: 심볼
            model_version: 모델 버전
            evaluation_days: 평가 기간
            include_visualizations: 시각화 포함 여부

        Returns:
            평가 결과
        """
        logger.info(
            "model_evaluation_started",
            symbol=symbol,
            model_version=model_version,
            evaluation_days=evaluation_days,
        )

        try:
            # 비동기로 평가 실행
            evaluation_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.evaluator.evaluate_model_performance,
                symbol,
                model_version,
                evaluation_days,
                include_visualizations,
            )

            logger.info(
                "model_evaluation_completed",
                symbol=symbol,
                model_version=evaluation_result.get("model_info", {}).get(
                    "model_version"
                ),
                overall_accuracy=evaluation_result.get("overall_performance", {}).get(
                    "avg_direction_accuracy", 0
                ),
            )

            return evaluation_result

        except Exception as e:
            logger.error(
                "model_evaluation_failed",
                symbol=symbol,
                model_version=model_version,
                error=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def run_backtest(
        self,
        symbol: str,
        model_version: str,
        start_date: date,
        end_date: date,
        strategy: str = "direction_based",
        backtest_config: Optional[BacktestConfig] = None,
    ) -> Dict[str, Any]:
        """
        백테스트 실행

        Args:
            symbol: 심볼
            model_version: 모델 버전
            start_date: 시작 날짜
            end_date: 종료 날짜
            strategy: 거래 전략
            backtest_config: 백테스트 설정

        Returns:
            백테스트 결과
        """
        logger.info(
            "backtest_started",
            symbol=symbol,
            model_version=model_version,
            start_date=start_date,
            end_date=end_date,
            strategy=strategy,
        )

        try:
            backtester = Backtester(backtest_config)

            # 비동기로 백테스트 실행
            backtest_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                backtester.run_backtest,
                symbol,
                model_version,
                start_date,
                end_date,
                strategy,
            )

            logger.info(
                "backtest_completed",
                symbol=symbol,
                model_version=model_version,
                total_return=backtest_result.get("performance_metrics", {}).get(
                    "total_return_pct", 0
                ),
                sharpe_ratio=backtest_result.get("risk_metrics", {}).get(
                    "sharpe_ratio", 0
                ),
            )

            return backtest_result

        except Exception as e:
            logger.error(
                "backtest_failed",
                symbol=symbol,
                model_version=model_version,
                error=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def update_prediction_results(
        self, target_date: Optional[date] = None, symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        예측 결과 업데이트

        Args:
            target_date: 업데이트할 날짜
            symbols: 특정 심볼들만 업데이트

        Returns:
            업데이트 결과
        """
        target_date = target_date or (date.today() - timedelta(days=1))

        logger.info(
            "prediction_results_update_started",
            target_date=target_date,
            symbols=symbols,
        )

        try:
            # 비동기로 업데이트 실행
            update_result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.result_tracker.update_prediction_results,
                target_date,
                symbols,
            )

            logger.info(
                "prediction_results_update_completed",
                target_date=target_date,
                updated_predictions=update_result.get("updated_predictions", 0),
                failed_updates=update_result.get("failed_updates", 0),
            )

            return update_result

        except Exception as e:
            logger.error(
                "prediction_results_update_failed",
                target_date=target_date,
                error=str(e),
            )
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_prediction_history(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        timeframe: Optional[str] = None,
        include_actual_results: bool = True,
    ) -> Dict[str, Any]:
        """
        예측 이력 조회

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            timeframe: 타임프레임 필터
            include_actual_results: 실제 결과 포함 여부

        Returns:
            예측 이력
        """
        end_date = end_date or date.today()
        start_date = start_date or (end_date - timedelta(days=30))

        logger.info(
            "prediction_history_query_started",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )

        session = SessionLocal()
        prediction_repo = MLPredictionRepository(session)

        try:
            # 예측 이력 조회
            predictions = prediction_repo.find_by_symbol_and_date_range(
                symbol=symbol, start_date=start_date, end_date=end_date
            )

            # 타임프레임 필터링
            if timeframe:
                predictions = [
                    pred
                    for pred in predictions
                    if pred.prediction_timeframe == timeframe
                ]

            # 실제 결과가 있는 것만 필터링
            if include_actual_results:
                predictions_with_results = [
                    pred for pred in predictions if pred.actual_price is not None
                ]
            else:
                predictions_with_results = predictions

            # 결과 구성
            history_data = []
            for pred in predictions:
                history_data.append(
                    {
                        "id": pred.id,
                        "prediction_date": pred.prediction_date.isoformat(),
                        "target_date": pred.target_date.isoformat(),
                        "timeframe": pred.prediction_timeframe,
                        "predicted_price": float(pred.predicted_price),
                        "actual_price": (
                            float(pred.actual_price) if pred.actual_price else None
                        ),
                        "predicted_direction": pred.predicted_direction,
                        "is_direction_correct": pred.is_direction_correct,
                        "confidence_score": float(pred.confidence_score),
                        "price_error_percent": (
                            float(pred.price_error_percent)
                            if pred.price_error_percent
                            else None
                        ),
                        "model_version": pred.model_version,
                        "batch_id": pred.batch_id,
                    }
                )

            # 통계 계산
            if predictions_with_results:
                total_predictions = len(predictions_with_results)
                correct_directions = sum(
                    1 for pred in predictions_with_results if pred.is_direction_correct
                )
                direction_accuracy = correct_directions / total_predictions

                avg_error = sum(
                    float(pred.price_error_percent)
                    for pred in predictions_with_results
                    if pred.price_error_percent is not None
                ) / len(
                    [
                        pred
                        for pred in predictions_with_results
                        if pred.price_error_percent is not None
                    ]
                )
            else:
                total_predictions = 0
                direction_accuracy = 0.0
                avg_error = 0.0

            result = {
                "symbol": symbol,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "filter": {
                    "timeframe": timeframe,
                    "include_actual_results": include_actual_results,
                },
                "statistics": {
                    "total_predictions": len(predictions),
                    "predictions_with_results": len(predictions_with_results),
                    "direction_accuracy": direction_accuracy,
                    "avg_error_percent": avg_error,
                },
                "predictions": history_data,
                "retrieved_at": datetime.now().isoformat(),
            }

            logger.info(
                "prediction_history_query_completed",
                symbol=symbol,
                total_predictions=len(predictions),
                predictions_with_results=len(predictions_with_results),
            )

            return result

        except Exception as e:
            logger.error("prediction_history_query_failed", symbol=symbol, error=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }
        finally:
            session.close()

    async def _check_existing_model(self, symbol: str) -> Optional[Dict[str, Any]]:
        """기존 모델 확인"""
        session = SessionLocal()
        model_repo = MLModelRepository(session)

        try:
            active_model = model_repo.find_active_model("lstm", symbol)

            if active_model:
                return {
                    "model_name": active_model.model_name,
                    "model_version": active_model.model_version,
                    "model_type": active_model.model_type,
                    "training_date": (
                        active_model.training_end_date.isoformat()
                        if active_model.training_end_date
                        else None
                    ),
                    "is_active": active_model.is_active,
                }

            return None

        finally:
            session.close()

    async def get_service_status(self) -> Dict[str, Any]:
        """서비스 상태 조회"""
        return {
            "service": "MLPredictionService",
            "status": "running",
            "config": {
                "model_storage_path": self.config.storage.base_model_path,
                "prediction_timeframes": self.config.model.target_days,
                "sequence_length": self.config.model.window_size,
            },
            "components": {
                "trainer": "ready",
                "predictor": "ready",
                "evaluator": "ready",
                "result_tracker": "ready",
            },
            "executor": {
                "max_workers": self.executor._max_workers,
                "active_threads": (
                    len(self.executor._threads)
                    if hasattr(self.executor, "_threads")
                    else 0
                ),
            },
            "timestamp": datetime.now().isoformat(),
        }

    def __del__(self):
        """소멸자 - 리소스 정리"""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=False)

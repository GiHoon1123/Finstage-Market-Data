"""
예측 실행기

이 파일은 훈련된 ML 모델을 사용하여 실제 예측을 수행하는 클래스를 구현합니다.
모델 로드, 데이터 전처리, 예측 실행, 결과 후처리까지의 전체 과정을 관리합니다.

주요 기능:
- 멀티 타임프레임 예측 실행
- 예측 신뢰도 계산
- 예측 결과 저장 및 추적
- 배치 예측 지원
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import uuid
import os

from app.ml_prediction.ml.model.lstm_model import MultiOutputLSTMPredictor
from app.ml_prediction.ml.data.preprocessor import MLDataPreprocessor
from app.ml_prediction.infra.model.entity.ml_prediction import MLPrediction
from app.ml_prediction.infra.model.entity.ml_model import MLModel
from app.ml_prediction.infra.model.repository.ml_prediction_repository import (
    MLPredictionRepository,
)
from app.ml_prediction.infra.model.repository.ml_model_repository import (
    MLModelRepository,
)
from app.ml_prediction.config.ml_config import ml_settings
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MultiTimeframePredictor:
    """
    멀티 타임프레임 예측기

    훈련된 LSTM 모델을 사용하여 7일, 14일, 30일 후 가격을 동시에 예측합니다.
    """

    def __init__(
        self,
        preprocessor: Optional[MLDataPreprocessor] = None,
        confidence_method: str = None,
    ):
        """
        예측기 초기화

        Args:
            preprocessor: 데이터 전처리기
            confidence_method: 신뢰도 계산 방법
        """
        self.preprocessor = preprocessor or MLDataPreprocessor()
        self.confidence_method = (
            confidence_method or ml_settings.prediction.confidence_method
        )

        # 로드된 모델들 캐시
        self.loaded_models: Dict[str, Tuple[MultiOutputLSTMPredictor, MLModel]] = {}

        # 예측 세션 정보
        self.current_predictions = {}

        logger.info(
            "multi_timeframe_predictor_initialized",
            confidence_method=self.confidence_method,
        )

    def predict_price(
        self,
        symbol: str,
        prediction_date: date = None,
        model_version: Optional[str] = None,
        save_prediction: bool = True,
    ) -> Dict[str, Any]:
        """
        가격 예측 실행

        Args:
            symbol: 심볼
            prediction_date: 예측 기준 날짜 (기본값: 오늘)
            model_version: 사용할 모델 버전 (기본값: 최신 활성 모델)
            save_prediction: 예측 결과 저장 여부

        Returns:
            예측 결과 딕셔너리
        """
        prediction_date = prediction_date or date.today()
        batch_id = str(uuid.uuid4())

        logger.info(
            "price_prediction_started",
            symbol=symbol,
            prediction_date=prediction_date,
            batch_id=batch_id,
        )

        try:
            # 1. 모델 로드
            try:
                model_predictor, model_entity = self._load_model(symbol, model_version)
                logger.debug(
                    "model_loaded_successfully",
                    symbol=symbol,
                    model_entity_type=(
                        type(model_entity).__name__ if model_entity else None
                    ),
                    has_model_version=(
                        hasattr(model_entity, "model_version")
                        if model_entity
                        else False
                    ),
                    model_version_value=(
                        getattr(model_entity, "model_version", None)
                        if model_entity
                        else None
                    ),
                )
            except Exception as e:
                logger.error(
                    "model_load_failed_in_predict", symbol=symbol, error=str(e)
                )
                raise

            # 2. 예측용 데이터 준비
            try:
                X_pred, data_metadata = self.preprocessor.prepare_prediction_data(
                    symbol=symbol, end_date=prediction_date
                )
                logger.debug("prediction_data_prepared", symbol=symbol)
            except Exception as e:
                logger.error("data_preparation_failed", symbol=symbol, error=str(e))
                raise

            # 3. 예측 실행
            try:
                raw_predictions = model_predictor.predict(X_pred)
                logger.debug("raw_prediction_completed", symbol=symbol)
            except Exception as e:
                logger.error("raw_prediction_failed", symbol=symbol, error=str(e))
                raise

            # 4. 예측 결과 역정규화
            try:
                denormalized_predictions = (
                    self.preprocessor.feature_engineer.denormalize_predictions(
                        raw_predictions
                    )
                )
                logger.debug("denormalization_completed", symbol=symbol)
            except Exception as e:
                logger.error("denormalization_failed", symbol=symbol, error=str(e))
                raise

            # 5. 신뢰도 계산
            try:
                confidence_scores = self._calculate_confidence_scores(
                    model_predictor, X_pred, raw_predictions
                )
                logger.debug("confidence_calculation_completed", symbol=symbol)
            except Exception as e:
                logger.error(
                    "confidence_calculation_failed", symbol=symbol, error=str(e)
                )
                raise

            # 6. 예측 결과 구성
            current_price = data_metadata.get("last_price", 0.0)
            prediction_results = []

            for timeframe, predicted_price in denormalized_predictions.items():
                days = int(timeframe.replace("d", ""))
                target_date = prediction_date + timedelta(days=days)

                # 가격 변화율 계산
                price_change_percent = (
                    (predicted_price[0] - current_price) / current_price
                ) * 100

                # 예측 방향 결정
                if price_change_percent > 0.5:
                    predicted_direction = "up"
                elif price_change_percent < -0.5:
                    predicted_direction = "down"
                else:
                    predicted_direction = "neutral"

                prediction_result = {
                    "timeframe": timeframe,
                    "target_date": target_date,
                    "predicted_price": float(predicted_price[0]),
                    "predicted_direction": predicted_direction,
                    "price_change_percent": float(price_change_percent),
                    "confidence_score": confidence_scores.get(timeframe, 0.5),
                }

                prediction_results.append(prediction_result)

            # 7. 예측 일관성 검증
            consistency_score = self._calculate_consistency_score(prediction_results)

            # 8. 최종 예측 결과
            final_result = {
                "status": "success",
                "batch_id": batch_id,
                "symbol": symbol,
                "prediction_date": prediction_date,
                "current_price": current_price,
                "model_id": getattr(model_entity, "id", None) if model_entity else None,
                "model_version": (
                    getattr(model_entity, "model_version", "unknown")
                    if model_entity
                    else "unknown"
                ),
                "model_type": (
                    getattr(model_entity, "model_type", "lstm")
                    if model_entity
                    else "lstm"
                ),
                "predictions": prediction_results,
                "consistency_score": consistency_score,
                "data_metadata": data_metadata,
                "created_at": datetime.now().isoformat(),
            }

            # 9. 예측 결과 저장 (predictor 레벨에서는 비활성화, 서비스 레벨에서 처리)
            # if save_prediction:
            #     try:
            #         self._save_predictions(final_result, model_entity)
            #     except Exception as save_error:
            #         logger.warning(
            #             "prediction_save_failed",
            #             symbol=symbol,
            #             batch_id=batch_id,
            #             error=str(save_error),
            #         )

            # 10. 캐시에 저장
            self.current_predictions[batch_id] = final_result

            logger.info(
                "price_prediction_completed",
                symbol=symbol,
                batch_id=batch_id,
                predictions_count=len(prediction_results),
                consistency_score=consistency_score,
            )

            return final_result

        except Exception as e:
            logger.error(
                "price_prediction_failed",
                symbol=symbol,
                batch_id=batch_id,
                error=str(e),
            )
            raise

    def predict_batch(
        self,
        symbols: List[str],
        prediction_date: date = None,
        save_predictions: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """
        여러 심볼에 대한 배치 예측

        Args:
            symbols: 심볼 목록
            prediction_date: 예측 기준 날짜
            save_predictions: 예측 결과 저장 여부

        Returns:
            심볼별 예측 결과 딕셔너리
        """
        prediction_date = prediction_date or date.today()

        logger.info(
            "batch_prediction_started", symbols=symbols, prediction_date=prediction_date
        )

        results = {}

        for symbol in symbols:
            try:
                result = self.predict_price(
                    symbol=symbol,
                    prediction_date=prediction_date,
                    save_prediction=save_predictions,
                )
                results[symbol] = result

                logger.debug(
                    "batch_prediction_completed_for_symbol",
                    symbol=symbol,
                    batch_id=result["batch_id"],
                )

            except Exception as e:
                logger.error(
                    "batch_prediction_failed_for_symbol", symbol=symbol, error=str(e)
                )
                results[symbol] = {"error": str(e), "status": "failed"}

        successful_predictions = len([r for r in results.values() if "error" not in r])

        logger.info(
            "batch_prediction_completed",
            total_symbols=len(symbols),
            successful=successful_predictions,
            failed=len(symbols) - successful_predictions,
        )

        return results

    def _load_model(
        self, symbol: str, model_version: Optional[str] = None
    ) -> Tuple[MultiOutputLSTMPredictor, MLModel]:
        """
        모델 로드 (캐시 활용)

        Args:
            symbol: 심볼
            model_version: 모델 버전

        Returns:
            (모델 예측기, 모델 엔티티) 튜플
        """
        cache_key = f"{symbol}_{model_version or 'active'}"

        # 캐시에서 확인
        if cache_key in self.loaded_models:
            logger.debug("model_loaded_from_cache", cache_key=cache_key)
            return self.loaded_models[cache_key]

        # 데이터베이스에서 모델 정보 조회
        session = SessionLocal()
        model_repository = MLModelRepository(session)

        try:
            if model_version:
                # 특정 버전 모델 조회
                model_entity = model_repository.find_by_name_and_version(
                    f"{symbol.replace('^', '')}_lstm", model_version
                )
            else:
                # 활성 모델 조회
                model_entity = model_repository.find_active_model("lstm", symbol)

            if not model_entity:
                raise ValueError(f"No suitable model found for {symbol}")

            # 모델 파일 로드
            model_predictor = MultiOutputLSTMPredictor(
                input_shape=(
                    ml_settings.model.window_size,
                    0,
                ),  # 실제 크기는 로드 시 결정
                config=ml_settings.model,
                model_name=model_entity.model_name,
            )

            model_predictor.load_model(
                filepath=model_entity.model_path,
                load_format=ml_settings.storage.model_format,
            )

            # 스케일러 로드
            scaler_dir = os.path.join(
                os.path.dirname(model_entity.model_path), "scalers"
            )
            if os.path.exists(scaler_dir):
                self.preprocessor.feature_engineer.load_scalers(scaler_dir)

            # 캐시에 저장
            self.loaded_models[cache_key] = (model_predictor, model_entity)

            logger.info(
                "model_loaded",
                symbol=symbol,
                model_name=(
                    getattr(model_entity, "model_name", "unknown")
                    if model_entity
                    else "unknown"
                ),
                model_version=(
                    getattr(model_entity, "model_version", "unknown")
                    if model_entity
                    else "unknown"
                ),
                cache_key=cache_key,
            )

            return model_predictor, model_entity

        except Exception as e:
            logger.error(
                "model_load_failed",
                symbol=symbol,
                model_version=model_version,
                error=str(e),
            )
            raise
        finally:
            session.close()

    def _calculate_confidence_scores(
        self,
        model_predictor: MultiOutputLSTMPredictor,
        X_pred: np.ndarray,
        predictions: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """
        예측 신뢰도 점수 계산

        Args:
            model_predictor: 모델 예측기
            X_pred: 입력 데이터
            predictions: 예측 결과

        Returns:
            타임프레임별 신뢰도 점수
        """
        confidence_scores = {}

        if self.confidence_method == "ensemble":
            # 앙상블 방법: 여러 번 예측하여 분산 계산
            confidence_scores = self._calculate_ensemble_confidence(
                model_predictor, X_pred, predictions
            )
        elif self.confidence_method == "dropout":
            # 드롭아웃 방법: 드롭아웃을 활성화한 상태에서 여러 번 예측
            confidence_scores = self._calculate_dropout_confidence(
                model_predictor, X_pred, predictions
            )
        else:
            # 기본값: 고정 신뢰도
            for timeframe in predictions.keys():
                confidence_scores[timeframe] = 0.7  # 기본 신뢰도 70%

        return confidence_scores

    def _calculate_ensemble_confidence(
        self,
        model_predictor: MultiOutputLSTMPredictor,
        X_pred: np.ndarray,
        base_predictions: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """앙상블 기반 신뢰도 계산"""
        confidence_scores = {}
        n_samples = ml_settings.prediction.confidence_samples

        try:
            # 여러 번 예측 수행
            all_predictions = []
            for _ in range(n_samples):
                pred = model_predictor.predict(X_pred, verbose=0)
                all_predictions.append(pred)

            # 각 타임프레임별 신뢰도 계산
            for timeframe in base_predictions.keys():
                predictions_array = np.array(
                    [pred[timeframe][0] for pred in all_predictions]
                )

                # 표준편차를 기반으로 신뢰도 계산 (낮은 분산 = 높은 신뢰도)
                std = np.std(predictions_array)
                mean_pred = np.mean(predictions_array)

                # 상대적 표준편차를 신뢰도로 변환 (0~1 범위)
                if mean_pred != 0:
                    relative_std = std / abs(mean_pred)
                    confidence = max(0.1, min(0.9, 1.0 - relative_std))
                else:
                    confidence = 0.5

                confidence_scores[timeframe] = float(confidence)

        except Exception as e:
            logger.warning("ensemble_confidence_calculation_failed", error=str(e))
            # 실패 시 기본값 사용
            for timeframe in base_predictions.keys():
                confidence_scores[timeframe] = 0.6

        return confidence_scores

    def _calculate_dropout_confidence(
        self,
        model_predictor: MultiOutputLSTMPredictor,
        X_pred: np.ndarray,
        base_predictions: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """드롭아웃 기반 신뢰도 계산 (Monte Carlo Dropout)"""
        # 현재 구현에서는 간단한 버전으로 구현
        # 실제로는 모델의 드롭아웃 레이어를 활성화한 상태에서 여러 번 예측
        confidence_scores = {}

        for timeframe in base_predictions.keys():
            # 기본 신뢰도 (실제 구현에서는 MC Dropout 사용)
            confidence_scores[timeframe] = 0.65

        return confidence_scores

    def _calculate_consistency_score(
        self, prediction_results: List[Dict[str, Any]]
    ) -> float:
        """
        예측 일관성 점수 계산

        Args:
            prediction_results: 예측 결과 목록

        Returns:
            일관성 점수 (0.0 ~ 1.0)
        """
        if len(prediction_results) < 2:
            return 1.0

        # 가격 변화율의 방향 일관성 확인
        directions = [result["predicted_direction"] for result in prediction_results]

        # 모든 방향이 같으면 높은 일관성
        if len(set(directions)) == 1:
            consistency = 0.9
        elif len(set(directions)) == 2:
            consistency = 0.6
        else:
            consistency = 0.3

        # 가격 변화율의 크기 일관성 확인
        price_changes = [
            abs(result["price_change_percent"]) for result in prediction_results
        ]

        if len(price_changes) > 1:
            # 변화율의 표준편차가 작을수록 일관성 높음
            std_change = np.std(price_changes)
            mean_change = np.mean(price_changes)

            if mean_change > 0:
                relative_std = std_change / mean_change
                magnitude_consistency = max(0.1, min(0.9, 1.0 - relative_std / 2))
            else:
                magnitude_consistency = 0.5

            # 방향 일관성과 크기 일관성의 가중 평균
            consistency = 0.7 * consistency + 0.3 * magnitude_consistency

        return float(consistency)

    def _save_predictions(
        self, prediction_result: Dict[str, Any], model_entity: MLModel
    ) -> List[MLPrediction]:
        """
        예측 결과를 데이터베이스에 저장

        Args:
            prediction_result: 예측 결과
            model_entity: 모델 엔티티

        Returns:
            저장된 예측 엔티티 목록
        """
        session = SessionLocal()
        repository = MLPredictionRepository(session)

        try:
            saved_predictions = []

            # 디버깅: model_entity 확인
            logger.info(
                "saving_predictions_debug",
                model_entity_exists=model_entity is not None,
                model_entity_type=type(model_entity).__name__ if model_entity else None,
                has_model_version=(
                    hasattr(model_entity, "model_version") if model_entity else False
                ),
            )

            for pred in prediction_result["predictions"]:
                # 안전한 model_version 추출
                safe_model_version = "unknown"
                safe_model_type = "lstm"

                if model_entity:
                    try:
                        safe_model_version = (
                            getattr(model_entity, "model_version", "unknown")
                            or "unknown"
                        )
                        safe_model_type = (
                            getattr(model_entity, "model_type", "lstm") or "lstm"
                        )
                    except Exception as attr_error:
                        logger.warning(
                            "model_entity_attribute_access_failed",
                            error=str(attr_error),
                            model_entity_type=type(model_entity).__name__,
                        )

                # MLPrediction 엔티티 생성
                prediction_entity = MLPrediction.create_prediction(
                    symbol=prediction_result["symbol"],
                    prediction_date=prediction_result["prediction_date"],
                    timeframe=pred["timeframe"],
                    target_date=pred["target_date"],
                    batch_id=prediction_result["batch_id"],
                    current_price=prediction_result["current_price"],
                    predicted_price=pred["predicted_price"],
                    confidence_score=pred["confidence_score"],
                    model_version=safe_model_version,
                    model_type=safe_model_type,
                    features_used=prediction_result["data_metadata"].get(
                        "feature_names", []
                    ),
                )

                # 데이터베이스에 저장
                saved_prediction = repository.save(prediction_entity)
                if saved_prediction:
                    saved_predictions.append(saved_prediction)

            logger.info(
                "predictions_saved_to_database",
                batch_id=prediction_result["batch_id"],
                symbol=prediction_result["symbol"],
                saved_count=len(saved_predictions),
            )

            return saved_predictions

        except Exception as e:
            logger.error(
                "prediction_save_failed",
                batch_id=prediction_result["batch_id"],
                error=str(e),
            )
            return []
        finally:
            session.close()

    def get_recent_predictions(
        self, symbol: str, days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        최근 예측 결과 조회

        Args:
            symbol: 심볼
            days: 최근 며칠간의 예측

        Returns:
            예측 결과 목록
        """
        session = SessionLocal()
        repository = MLPredictionRepository(session)

        try:
            predictions = repository.find_recent_predictions(symbol, days)

            # 배치별로 그룹화
            batch_groups = {}
            for pred in predictions:
                batch_id = pred.batch_id
                if batch_id not in batch_groups:
                    batch_groups[batch_id] = []
                batch_groups[batch_id].append(pred.to_dict())

            # 배치별 결과 구성
            results = []
            for batch_id, batch_predictions in batch_groups.items():
                if batch_predictions:
                    result = {
                        "batch_id": batch_id,
                        "symbol": symbol,
                        "prediction_date": batch_predictions[0]["prediction_date"],
                        "predictions": batch_predictions,
                        "model_version": batch_predictions[0]["model"]["model_version"],
                    }
                    results.append(result)

            # 날짜순 정렬
            results.sort(key=lambda x: x["prediction_date"], reverse=True)

            return results

        except Exception as e:
            logger.error("recent_predictions_query_failed", symbol=symbol, error=str(e))
            return []
        finally:
            session.close()

    def clear_model_cache(self) -> None:
        """모델 캐시 초기화"""
        self.loaded_models.clear()
        logger.info("model_cache_cleared")

    def get_predictor_stats(self) -> Dict[str, Any]:
        """예측기 통계 정보 반환"""
        return {
            "loaded_models_count": len(self.loaded_models),
            "loaded_models": list(self.loaded_models.keys()),
            "current_predictions_count": len(self.current_predictions),
            "confidence_method": self.confidence_method,
            "config": {
                "confidence_samples": ml_settings.prediction.confidence_samples,
                "consistency_threshold": ml_settings.prediction.consistency_threshold,
            },
        }

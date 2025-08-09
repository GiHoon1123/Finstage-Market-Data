"""
모델 훈련기

이 파일은 ML 모델의 훈련 과정을 관리하는 트레이너 클래스를 구현합니다.
데이터 준비부터 모델 훈련, 평가, 저장까지의 전체 워크플로우를 제공합니다.

주요 기능:
- 통합 모델 훈련 파이프라인
- 하이퍼파라미터 튜닝 지원
- 훈련 과정 모니터링
- 모델 성능 평가 및 저장
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import date, datetime, timedelta
import numpy as np
import pandas as pd
import os
import json
import uuid
from dataclasses import asdict

from app.ml_prediction.ml.model.lstm_model import MultiOutputLSTMPredictor
from app.ml_prediction.ml.data.preprocessor import MLDataPreprocessor
from app.ml_prediction.infra.model.entity.ml_model import MLModel
from app.ml_prediction.infra.model.repository.ml_model_repository import (
    MLModelRepository,
)
from app.ml_prediction.config.ml_config import ml_settings, ModelConfig, TrainingConfig
from app.common.infra.database.config.database_config import SessionLocal
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class ModelTrainer:
    """
    모델 훈련기

    ML 모델의 전체 훈련 과정을 관리하고 실행합니다.
    """

    def __init__(
        self,
        model_config: Optional[ModelConfig] = None,
        training_config: Optional[TrainingConfig] = None,
        preprocessor: Optional[MLDataPreprocessor] = None,
    ):
        """
        훈련기 초기화

        Args:
            model_config: 모델 설정
            training_config: 훈련 설정
            preprocessor: 데이터 전처리기
        """
        self.model_config = model_config or ml_settings.model
        self.training_config = training_config or ml_settings.training
        self.preprocessor = preprocessor or MLDataPreprocessor()

        # 현재 훈련 세션 정보
        self.current_session = None
        self.training_results = {}

        try:
            model_config_dict = (
                asdict(self.model_config)
                if hasattr(self.model_config, "__dataclass_fields__")
                else str(self.model_config)
            )
            training_config_dict = (
                asdict(self.training_config)
                if hasattr(self.training_config, "__dataclass_fields__")
                else str(self.training_config)
            )

            logger.info(
                "model_trainer_initialized",
                model_config=model_config_dict,
                training_config=training_config_dict,
            )
        except Exception as e:
            logger.warning("model_trainer_config_logging_failed", error=str(e))

    def train_model(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        save_model: bool = True,
        force_retrain: bool = False,
    ) -> Dict[str, Any]:
        """
        모델 훈련 실행

        Args:
            symbol: 심볼
            start_date: 훈련 데이터 시작 날짜
            end_date: 훈련 데이터 종료 날짜
            model_name: 모델 이름
            model_version: 모델 버전
            save_model: 모델 저장 여부
            force_retrain: 강제 재훈련 여부

        Returns:
            훈련 결과 딕셔너리
        """
        # 훈련 세션 시작
        session_id = str(uuid.uuid4())
        self.current_session = {
            "session_id": session_id,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "started_at": datetime.now(),
        }

        model_name = model_name or f"{symbol.replace('^', '')}_lstm"
        model_version = model_version or self._generate_version()

        logger.info(
            "model_training_session_started",
            session_id=session_id,
            symbol=symbol,
            model_name=model_name,
            model_version=model_version,
            date_range_days=(end_date - start_date).days,
        )

        try:
            # 1. 데이터 준비
            logger.info("preparing_training_data")
            X_splits, y_splits, data_metadata = self.preprocessor.prepare_training_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                force_refresh=force_retrain,
            )

            # 2. 모델 생성 및 구성
            logger.info("building_model")
            input_shape = (X_splits["train"].shape[1], X_splits["train"].shape[2])

            model_predictor = MultiOutputLSTMPredictor(
                input_shape=input_shape, config=self.model_config, model_name=model_name
            )

            # 모델 구조 생성
            model_predictor.build_multi_output_model()

            # 모델 컴파일
            model_predictor.compile_model(
                optimizer=self.model_config.optimizer,
                loss=self.model_config.loss,
                metrics=self.model_config.metrics,
                loss_weights=self.model_config.loss_weights,
            )

            # 3. 모델 훈련
            logger.info("starting_model_training")
            training_metadata = model_predictor.train(
                X_train=X_splits["train"],
                y_train={
                    timeframe: splits["train"] for timeframe, splits in y_splits.items()
                },
                X_val=X_splits["val"],
                y_val={
                    timeframe: splits["val"] for timeframe, splits in y_splits.items()
                },
                epochs=self.training_config.epochs,
                batch_size=self.training_config.batch_size,
                verbose=1,
            )

            # 4. 모델 평가
            logger.info("evaluating_model")
            test_y = {
                timeframe: splits["test"] for timeframe, splits in y_splits.items()
            }
            evaluation_results = model_predictor.evaluate(
                X_test=X_splits["test"],
                y_test=test_y,
                batch_size=self.training_config.batch_size,
            )

            # 5. 성능 지표 계산
            performance_metrics = self._calculate_performance_metrics(
                model_predictor, X_splits["test"], test_y
            )

            # 6. 모델 저장
            model_path = None
            if save_model:
                model_path = self._save_trained_model(
                    model_predictor, model_name, model_version, symbol
                )

            # 7. 데이터베이스에 모델 메타데이터 저장
            model_entity = None
            if save_model:
                model_entity = self._save_model_metadata(
                    model_name=model_name,
                    model_version=model_version,
                    symbol=symbol,
                    model_path=model_path,
                    training_metadata=training_metadata,
                    data_metadata=data_metadata,
                    performance_metrics=performance_metrics,
                    evaluation_results=evaluation_results,
                )

            # 8. 훈련 결과 정리
            training_results = {
                "status": "success",
                "session_id": session_id,
                "model_name": model_name,
                "model_version": model_version,
                "symbol": symbol,
                "model_path": model_path,
                "model_id": model_entity.id if model_entity else None,
                "training_metadata": training_metadata,
                "evaluation_results": evaluation_results,
                "performance_metrics": performance_metrics,
                "data_metadata": data_metadata,
                "training_config": (
                    asdict(self.training_config)
                    if hasattr(self.training_config, "__dataclass_fields__")
                    else str(self.training_config)
                ),
                "model_config": (
                    asdict(self.model_config)
                    if hasattr(self.model_config, "__dataclass_fields__")
                    else str(self.model_config)
                ),
                "completed_at": datetime.now().isoformat(),
            }

            self.training_results[session_id] = training_results

            logger.info(
                "model_training_session_completed",
                session_id=session_id,
                model_name=model_name,
                model_version=model_version,
                final_loss=training_metadata["final_loss"],
                training_duration_minutes=round(
                    training_metadata["training_duration_seconds"] / 60, 2
                ),
            )

            return training_results

        except Exception as e:
            logger.error(
                "model_training_session_failed", session_id=session_id, error=str(e)
            )
            raise
        finally:
            self.current_session = None

    def train_multiple_models(
        self,
        symbols: List[str],
        start_date: date,
        end_date: date,
        base_model_name: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        여러 심볼에 대해 모델 훈련

        Args:
            symbols: 심볼 목록
            start_date: 시작 날짜
            end_date: 종료 날짜
            base_model_name: 기본 모델 이름

        Returns:
            심볼별 훈련 결과 딕셔너리
        """
        results = {}

        logger.info(
            "multiple_model_training_started",
            symbols=symbols,
            date_range_days=(end_date - start_date).days,
        )

        for symbol in symbols:
            try:
                model_name = base_model_name or f"{symbol.replace('^', '')}_lstm"

                logger.info(
                    "training_model_for_symbol", symbol=symbol, model_name=model_name
                )

                result = self.train_model(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    model_name=model_name,
                    save_model=True,
                )

                results[symbol] = result

                logger.info(
                    "model_training_completed_for_symbol",
                    symbol=symbol,
                    model_name=model_name,
                )

            except Exception as e:
                logger.error(
                    "model_training_failed_for_symbol", symbol=symbol, error=str(e)
                )
                results[symbol] = {"error": str(e), "status": "failed"}

        logger.info(
            "multiple_model_training_completed",
            total_symbols=len(symbols),
            successful=len([r for r in results.values() if "error" not in r]),
            failed=len([r for r in results.values() if "error" in r]),
        )

        return results

    def _calculate_performance_metrics(
        self,
        model_predictor: MultiOutputLSTMPredictor,
        X_test: np.ndarray,
        y_test: Dict[str, np.ndarray],
    ) -> Dict[str, Dict[str, float]]:
        """
        성능 지표 계산

        Args:
            model_predictor: 훈련된 모델
            X_test: 테스트 특성 데이터
            y_test: 테스트 타겟 데이터

        Returns:
            타임프레임별 성능 지표
        """
        logger.debug("calculating_performance_metrics")

        # 예측 수행
        predictions = model_predictor.predict(X_test)

        performance_metrics = {}

        for timeframe in self.model_config.target_days:
            timeframe_key = f"{timeframe}d"

            if timeframe_key in predictions and timeframe_key in y_test:
                y_true = y_test[timeframe_key]
                y_pred = predictions[timeframe_key]

                # MSE 계산
                mse = float(np.mean((y_true - y_pred) ** 2))

                # MAE 계산
                mae = float(np.mean(np.abs(y_true - y_pred)))

                # RMSE 계산
                rmse = float(np.sqrt(mse))

                # 방향성 정확도 계산 (실제 구현에서는 이전 가격 정보 필요)
                # 여기서는 단순화된 버전으로 구현
                direction_accuracy = self._calculate_direction_accuracy(y_true, y_pred)

                # R² 점수 계산
                r2_score = self._calculate_r2_score(y_true, y_pred)

                performance_metrics[timeframe_key] = {
                    "mse": mse,
                    "mae": mae,
                    "rmse": rmse,
                    "direction_accuracy": direction_accuracy,
                    "r2_score": r2_score,
                }

                logger.debug(
                    "performance_metrics_calculated",
                    timeframe=timeframe_key,
                    mse=mse,
                    mae=mae,
                    direction_accuracy=direction_accuracy,
                )

        return performance_metrics

    def _calculate_direction_accuracy(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> float:
        """
        방향성 정확도 계산 (단순화된 버전)

        Args:
            y_true: 실제 값
            y_pred: 예측 값

        Returns:
            방향성 정확도
        """
        if len(y_true) < 2:
            return 0.0

        # 연속된 값들 간의 변화 방향 비교
        true_directions = np.diff(y_true) > 0
        pred_directions = np.diff(y_pred) > 0

        accuracy = np.mean(true_directions == pred_directions)
        return float(accuracy)

    def _calculate_r2_score(self, y_true: np.ndarray, y_pred: np.ndarray) -> float:
        """R² 점수 계산"""
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

        if ss_tot == 0:
            return 0.0

        r2 = 1 - (ss_res / ss_tot)
        return float(r2)

    def _save_trained_model(
        self,
        model_predictor: MultiOutputLSTMPredictor,
        model_name: str,
        model_version: str,
        symbol: str,
    ) -> str:
        """
        훈련된 모델 저장

        Args:
            model_predictor: 훈련된 모델
            model_name: 모델 이름
            model_version: 모델 버전
            symbol: 심볼

        Returns:
            저장된 모델 경로
        """
        # 모델 저장 경로 생성
        model_dir = ml_settings.get_model_save_path(model_name, model_version)
        model_extension = (
            ".keras" if ml_settings.storage.model_format == "keras" else ".h5"
        )
        model_path = os.path.join(model_dir, f"model{model_extension}")

        # 모델 저장
        model_predictor.save_model(
            filepath=model_path, save_format=ml_settings.storage.model_format
        )

        # 스케일러 저장
        scaler_dir = os.path.join(model_dir, "scalers")
        self.preprocessor.feature_engineer.save_scalers(scaler_dir)

        logger.info(
            "trained_model_saved",
            model_name=model_name,
            model_version=model_version,
            model_path=model_path,
        )

        return model_path

    def _save_model_metadata(
        self,
        model_name: str,
        model_version: str,
        symbol: str,
        model_path: str,
        training_metadata: Dict[str, Any],
        data_metadata: Dict[str, Any],
        performance_metrics: Dict[str, Dict[str, float]],
        evaluation_results: Dict[str, float],
    ) -> MLModel:
        """
        모델 메타데이터를 데이터베이스에 저장

        Returns:
            저장된 MLModel 엔티티
        """
        session = SessionLocal()
        repository = MLModelRepository(session)

        try:
            # 훈련 시작/종료 시간 파싱
            training_start = datetime.fromisoformat(
                training_metadata["training_start_time"]
            )
            training_end = datetime.fromisoformat(
                training_metadata["training_end_time"]
            )

            # 데이터 날짜 범위 파싱
            start_str = data_metadata["date_range"]["start"]
            end_str = data_metadata["date_range"]["end"]

            # 이미 date 객체인지 확인
            if isinstance(start_str, str):
                data_start = datetime.fromisoformat(start_str).date()
            else:
                data_start = start_str if hasattr(start_str, "year") else start_str

            if isinstance(end_str, str):
                data_end = datetime.fromisoformat(end_str).date()
            else:
                data_end = end_str if hasattr(end_str, "year") else end_str

            # MLModel 엔티티 생성
            model_entity = MLModel.create_model(
                model_name=model_name,
                model_version=model_version,
                model_type="lstm",
                symbol=symbol,
                model_path=model_path,
                training_start_date=training_start,
                training_end_date=training_end,
                epochs_trained=training_metadata["epochs_completed"],
                training_data_start_date=data_start,
                training_data_end_date=data_end,
                training_samples=training_metadata["train_samples"],
                validation_samples=training_metadata["val_samples"],
                test_samples=data_metadata["raw_data_info"]["records"]
                - training_metadata["train_samples"]
                - training_metadata["val_samples"],
                feature_count=data_metadata["feature_engineering"]["feature_count"],
                window_size=self.model_config.window_size,
                hyperparameters=(
                    asdict(self.model_config)
                    if hasattr(self.model_config, "__dataclass_fields__")
                    else str(self.model_config)
                ),
                training_config=(
                    asdict(self.training_config)
                    if hasattr(self.training_config, "__dataclass_fields__")
                    else str(self.training_config)
                ),
                description=f"Multi-output LSTM model for {symbol} price prediction",
            )

            # 성능 지표 설정
            for timeframe, metrics in performance_metrics.items():
                if timeframe == "7d":
                    model_entity.update_performance_metrics(
                        "7d",
                        metrics["mse"],
                        metrics["mae"],
                        metrics["direction_accuracy"],
                    )
                elif timeframe == "14d":
                    model_entity.update_performance_metrics(
                        "14d",
                        metrics["mse"],
                        metrics["mae"],
                        metrics["direction_accuracy"],
                    )
                elif timeframe == "30d":
                    model_entity.update_performance_metrics(
                        "30d",
                        metrics["mse"],
                        metrics["mae"],
                        metrics["direction_accuracy"],
                    )

            # 데이터베이스에 저장
            saved_model = repository.save(model_entity)

            if saved_model:
                # 모델을 활성 상태로 설정
                repository.activate_model(saved_model.id)

                logger.info(
                    "model_metadata_saved",
                    model_id=saved_model.id,
                    model_name=model_name,
                    model_version=model_version,
                    is_active=True,
                )
                return saved_model
            else:
                raise ValueError("Failed to save model metadata")

        except Exception as e:
            logger.error(
                "model_metadata_save_failed",
                model_name=model_name,
                model_version=model_version,
                error=str(e),
            )
            raise
        finally:
            session.close()

    def _generate_version(self) -> str:
        """모델 버전 생성"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"v1.0.0_{timestamp}"

    def get_training_session_info(self) -> Optional[Dict[str, Any]]:
        """현재 훈련 세션 정보 반환"""
        return self.current_session

    def get_training_results(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """훈련 결과 반환"""
        if session_id:
            return self.training_results.get(session_id, {})
        else:
            return self.training_results

    def clear_training_results(self) -> None:
        """훈련 결과 초기화"""
        self.training_results.clear()
        logger.info("training_results_cleared")

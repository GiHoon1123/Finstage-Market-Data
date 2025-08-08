"""
멀티 아웃풋 LSTM 모델

이 파일은 7일, 14일, 30일 동시 예측을 위한 멀티 아웃풋 LSTM 모델을 구현합니다.
TensorFlow/Keras를 사용하여 시계열 예측에 최적화된 구조를 제공합니다.

주요 기능:
- 멀티 아웃풋 LSTM 아키텍처
- 동적 모델 구조 생성
- 가중치 기반 손실 함수
- 모델 저장/로드 기능
"""

from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, Model, callbacks
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import MeanSquaredError
from tensorflow.keras.metrics import MeanAbsoluteError
import os
import json
from datetime import datetime

from app.ml_prediction.config.ml_config import ml_settings, ModelConfig
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)

# TensorFlow 로깅 레벨 설정
tf.get_logger().setLevel("ERROR")


class MultiOutputLSTMPredictor:
    """
    멀티 아웃풋 LSTM 기반 가격 예측 모델

    7일, 14일, 30일 후 가격을 동시에 예측하는 LSTM 모델입니다.
    각 출력에 대해 개별적인 Dense 레이어를 가지며, 가중치 기반 손실 함수를 사용합니다.
    """

    def __init__(
        self,
        input_shape: Tuple[int, int],
        config: Optional[ModelConfig] = None,
        model_name: str = "multi_output_lstm",
    ):
        """
        모델 초기화

        Args:
            input_shape: 입력 형태 (window_size, features)
            config: 모델 설정
            model_name: 모델 이름
        """
        self.input_shape = input_shape
        self.config = config or ml_settings.model
        self.model_name = model_name
        self.target_days = (
            self.config.target_days
            if hasattr(self.config, "target_days")
            else ml_settings.model.target_days
        )

        # 모델 관련 속성
        self.model: Optional[Model] = None
        self.training_history = None
        self.is_compiled = False

        # 메타데이터
        self.created_at = datetime.now()
        self.model_version = None
        self.training_metadata = {}

        logger.info(
            "multi_output_lstm_predictor_initialized",
            input_shape=input_shape,
            target_days=self.target_days,
            model_name=model_name,
        )

    def build_multi_output_model(self) -> Model:
        """
        멀티 아웃풋 LSTM 모델 구조 생성

        Returns:
            구성된 Keras 모델
        """
        logger.info(
            "building_multi_output_lstm_model",
            input_shape=self.input_shape,
            lstm_units=self.config.lstm_units,
            target_days=self.target_days,
        )

        # 입력 레이어
        inputs = layers.Input(shape=self.input_shape, name="price_sequence_input")

        # LSTM 레이어들
        x = inputs

        for i, units in enumerate(self.config.lstm_units):
            # 마지막 LSTM 레이어가 아니면 return_sequences=True
            return_sequences = i < len(self.config.lstm_units) - 1

            x = layers.LSTM(
                units=units,
                return_sequences=return_sequences,
                dropout=self.config.dropout_rate,
                recurrent_dropout=self.config.dropout_rate,
                name=f"lstm_{i+1}",
            )(x)

            # 배치 정규화 추가
            x = layers.BatchNormalization(name=f"batch_norm_lstm_{i+1}")(x)

        # 공통 Dense 레이어들
        for i, units in enumerate(self.config.dense_units):
            x = layers.Dense(
                units=units,
                activation=self.config.activation,
                name=f"dense_common_{i+1}",
            )(x)

            x = layers.Dropout(self.config.dropout_rate, name=f"dropout_common_{i+1}")(
                x
            )

        # 각 타임프레임별 출력 레이어
        outputs = {}
        output_layers = []

        for days in self.target_days:
            # 각 출력별 전용 Dense 레이어
            branch = layers.Dense(
                units=16,
                activation=self.config.activation,
                name=f"dense_{days}d_branch",
            )(x)

            branch = layers.Dropout(
                self.config.dropout_rate, name=f"dropout_{days}d_branch"
            )(branch)

            # 최종 출력 레이어 (선형 활성화)
            output = layers.Dense(
                units=1, activation="linear", name=f"price_prediction_{days}d"
            )(branch)

            outputs[f"{days}d"] = output
            output_layers.append(output)

        # 모델 생성
        self.model = Model(inputs=inputs, outputs=output_layers, name=self.model_name)

        # 모델 구조 로깅
        self._log_model_architecture()

        logger.info(
            "multi_output_lstm_model_built",
            total_params=self.model.count_params(),
            trainable_params=sum(
                [tf.keras.backend.count_params(w) for w in self.model.trainable_weights]
            ),
            outputs=list(outputs.keys()),
        )

        return self.model

    def compile_model(
        self,
        optimizer: Union[str, keras.optimizers.Optimizer] = None,
        loss: Union[str, Dict[str, str]] = None,
        metrics: Union[List[str], Dict[str, List[str]]] = None,
        loss_weights: Optional[List[float]] = None,
    ) -> None:
        """
        모델 컴파일

        Args:
            optimizer: 최적화 알고리즘
            loss: 손실 함수
            metrics: 평가 지표
            loss_weights: 출력별 손실 가중치
        """
        if self.model is None:
            raise ValueError("Model must be built before compilation")

        # 기본값 설정
        if optimizer is None:
            optimizer = Adam(learning_rate=0.001)
        elif isinstance(optimizer, str):
            if optimizer.lower() == "adam":
                optimizer = Adam(learning_rate=0.001)
            else:
                optimizer = optimizer

        if loss is None:
            loss = "mse"

        if metrics is None:
            metrics = ["mae"]

        if loss_weights is None:
            loss_weights = self.config.loss_weights

        # 멀티 아웃풋을 위한 손실 함수 및 지표 설정
        if isinstance(loss, str):
            # 모든 출력에 동일한 손실 함수 적용
            loss_dict = {f"price_prediction_{days}d": loss for days in self.target_days}
        else:
            loss_dict = loss

        if isinstance(metrics, list):
            # 모든 출력에 동일한 지표 적용
            metrics_dict = {
                f"price_prediction_{days}d": metrics for days in self.target_days
            }
        else:
            metrics_dict = metrics

        # 모델 컴파일
        self.model.compile(
            optimizer=optimizer,
            loss=loss_dict,
            metrics=metrics_dict,
            loss_weights=loss_weights,
        )

        self.is_compiled = True

        logger.info(
            "model_compiled",
            optimizer=type(optimizer).__name__,
            loss=loss_dict,
            loss_weights=loss_weights,
            metrics=(
                list(metrics_dict.keys()) if isinstance(metrics_dict, dict) else metrics
            ),
        )

    def train(
        self,
        X_train: np.ndarray,
        y_train: Dict[str, np.ndarray],
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[Dict[str, np.ndarray]] = None,
        epochs: int = None,
        batch_size: int = None,
        callbacks_list: Optional[List[callbacks.Callback]] = None,
        verbose: int = 1,
    ) -> Dict[str, Any]:
        """
        모델 훈련

        Args:
            X_train: 훈련 특성 데이터
            y_train: 훈련 타겟 데이터 (딕셔너리)
            X_val: 검증 특성 데이터
            y_val: 검증 타겟 데이터 (딕셔너리)
            epochs: 에포크 수
            batch_size: 배치 크기
            callbacks_list: 콜백 목록
            verbose: 로깅 레벨

        Returns:
            훈련 결과 딕셔너리
        """
        if not self.is_compiled:
            raise ValueError("Model must be compiled before training")

        # 기본값 설정
        epochs = epochs or ml_settings.training.epochs
        batch_size = batch_size or ml_settings.training.batch_size

        # y_train을 리스트 형태로 변환 (모델 출력 순서에 맞춤)
        y_train_list = [y_train[f"{days}d"] for days in self.target_days]

        validation_data = None
        if X_val is not None and y_val is not None:
            y_val_list = [y_val[f"{days}d"] for days in self.target_days]
            validation_data = (X_val, y_val_list)

        # 기본 콜백 설정
        if callbacks_list is None:
            callbacks_list = self._create_default_callbacks()

        logger.info(
            "model_training_started",
            train_samples=len(X_train),
            val_samples=len(X_val) if X_val is not None else 0,
            epochs=epochs,
            batch_size=batch_size,
            callbacks=len(callbacks_list),
        )

        # 훈련 시작 시간 기록
        training_start_time = datetime.now()

        try:
            # 모델 훈련
            history = self.model.fit(
                X_train,
                y_train_list,
                validation_data=validation_data,
                epochs=epochs,
                batch_size=batch_size,
                callbacks=callbacks_list,
                verbose=verbose,
                shuffle=True,  # 시계열이지만 윈도우 단위로는 셔플 가능
            )

            self.training_history = history

            # 훈련 완료 시간 기록
            training_end_time = datetime.now()
            training_duration = training_end_time - training_start_time

            # 훈련 메타데이터 저장
            self.training_metadata = {
                "training_start_time": training_start_time.isoformat(),
                "training_end_time": training_end_time.isoformat(),
                "training_duration_seconds": training_duration.total_seconds(),
                "epochs_completed": len(history.history["loss"]),
                "final_loss": float(history.history["loss"][-1]),
                "final_val_loss": (
                    float(history.history["val_loss"][-1])
                    if "val_loss" in history.history
                    else None
                ),
                "best_epoch": self._find_best_epoch(history),
                "train_samples": len(X_train),
                "val_samples": len(X_val) if X_val is not None else 0,
                "batch_size": batch_size,
            }

            logger.info(
                "model_training_completed",
                epochs_completed=self.training_metadata["epochs_completed"],
                training_duration_minutes=round(
                    training_duration.total_seconds() / 60, 2
                ),
                final_loss=self.training_metadata["final_loss"],
                final_val_loss=self.training_metadata["final_val_loss"],
            )

            return self.training_metadata

        except Exception as e:
            logger.error(
                "model_training_failed",
                error=str(e),
                epochs=epochs,
                batch_size=batch_size,
            )
            raise

    def predict(
        self, X: np.ndarray, batch_size: int = None, verbose: int = 0
    ) -> Dict[str, np.ndarray]:
        """
        예측 수행

        Args:
            X: 입력 데이터
            batch_size: 배치 크기
            verbose: 로깅 레벨

        Returns:
            타임프레임별 예측 결과 딕셔너리
        """
        if self.model is None:
            raise ValueError("Model must be built before prediction")

        batch_size = batch_size or ml_settings.training.batch_size

        logger.debug("prediction_started", input_shape=X.shape, batch_size=batch_size)

        try:
            # 예측 수행
            predictions_list = self.model.predict(
                X, batch_size=batch_size, verbose=verbose
            )

            # 리스트를 딕셔너리로 변환
            predictions_dict = {}
            for i, days in enumerate(self.target_days):
                predictions_dict[f"{days}d"] = predictions_list[i].flatten()

            logger.debug(
                "prediction_completed",
                predictions_count=len(predictions_list[0]),
                timeframes=list(predictions_dict.keys()),
            )

            return predictions_dict

        except Exception as e:
            logger.error("prediction_failed", error=str(e), input_shape=X.shape)
            raise

    def evaluate(
        self,
        X_test: np.ndarray,
        y_test: Dict[str, np.ndarray],
        batch_size: int = None,
        verbose: int = 0,
    ) -> Dict[str, float]:
        """
        모델 평가

        Args:
            X_test: 테스트 특성 데이터
            y_test: 테스트 타겟 데이터
            batch_size: 배치 크기
            verbose: 로깅 레벨

        Returns:
            평가 결과 딕셔너리
        """
        if self.model is None:
            raise ValueError("Model must be built before evaluation")

        batch_size = batch_size or ml_settings.training.batch_size

        # y_test를 리스트 형태로 변환
        y_test_list = [y_test[f"{days}d"] for days in self.target_days]

        logger.info(
            "model_evaluation_started", test_samples=len(X_test), batch_size=batch_size
        )

        try:
            # 모델 평가
            evaluation_results = self.model.evaluate(
                X_test,
                y_test_list,
                batch_size=batch_size,
                verbose=verbose,
                return_dict=True,
            )

            logger.info("model_evaluation_completed", results=evaluation_results)

            return evaluation_results

        except Exception as e:
            logger.error("model_evaluation_failed", error=str(e))
            raise

    def save_model(
        self, filepath: str, save_format: str = "keras", include_optimizer: bool = True
    ) -> None:
        """
        모델 저장

        Args:
            filepath: 저장 경로
            save_format: 저장 형식 ('keras', 'tf', 'h5')
            include_optimizer: 옵티마이저 포함 여부
        """
        if self.model is None:
            raise ValueError("No model to save")

        # 디렉토리 생성
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            # 모델 저장
            if save_format.lower() == "keras":
                self.model.save(filepath, include_optimizer=include_optimizer)
            elif save_format.lower() == "h5":
                self.model.save(f"{filepath}.h5", include_optimizer=include_optimizer)
            elif save_format.lower() == "tf":
                tf.saved_model.save(self.model, filepath)
            else:
                raise ValueError(f"Unsupported save format: {save_format}")

            # 메타데이터 저장
            metadata_path = f"{filepath}_metadata.json"
            self._save_metadata(metadata_path)

            logger.info(
                "model_saved",
                filepath=filepath,
                save_format=save_format,
                include_optimizer=include_optimizer,
            )

        except Exception as e:
            logger.error("model_save_failed", filepath=filepath, error=str(e))
            raise

    def load_model(
        self, filepath: str, load_format: str = "keras", compile_model: bool = True
    ) -> None:
        """
        모델 로드

        Args:
            filepath: 모델 파일 경로
            load_format: 로드 형식
            compile_model: 컴파일 여부
        """
        try:
            # 모델 로드
            if load_format.lower() == "keras":
                self.model = keras.models.load_model(filepath, compile=compile_model)
            elif load_format.lower() == "h5":
                self.model = keras.models.load_model(
                    f"{filepath}.h5", compile=compile_model
                )
            elif load_format.lower() == "tf":
                self.model = tf.saved_model.load(filepath)
            else:
                raise ValueError(f"Unsupported load format: {load_format}")

            self.is_compiled = compile_model

            # 메타데이터 로드
            metadata_path = f"{filepath}_metadata.json"
            self._load_metadata(metadata_path)

            logger.info(
                "model_loaded",
                filepath=filepath,
                load_format=load_format,
                compile_model=compile_model,
            )

        except Exception as e:
            logger.error("model_load_failed", filepath=filepath, error=str(e))
            raise

    def _create_default_callbacks(self) -> List[callbacks.Callback]:
        """기본 콜백 생성"""
        callback_list = []

        # 조기 종료
        early_stopping = callbacks.EarlyStopping(
            monitor=ml_settings.training.early_stopping_monitor,
            patience=ml_settings.training.early_stopping_patience,
            mode=ml_settings.training.early_stopping_mode,
            restore_best_weights=True,
            verbose=1,
        )
        callback_list.append(early_stopping)

        # 학습률 감소
        reduce_lr = callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            factor=ml_settings.training.reduce_lr_factor,
            patience=ml_settings.training.reduce_lr_patience,
            min_lr=ml_settings.training.min_lr,
            verbose=1,
        )
        callback_list.append(reduce_lr)

        return callback_list

    def _find_best_epoch(self, history) -> int:
        """최적 에포크 찾기"""
        if "val_loss" in history.history:
            return int(np.argmin(history.history["val_loss"]) + 1)
        else:
            return int(np.argmin(history.history["loss"]) + 1)

    def _log_model_architecture(self) -> None:
        """모델 구조 로깅"""
        if self.model is not None:
            # 모델 요약을 문자열로 캡처
            summary_lines = []
            self.model.summary(print_fn=lambda x: summary_lines.append(x))

            logger.debug("model_architecture", summary="\n".join(summary_lines))

    def _save_metadata(self, filepath: str) -> None:
        """메타데이터 저장"""
        metadata = {
            "model_name": self.model_name,
            "input_shape": self.input_shape,
            "target_days": self.target_days,
            "config": {
                "lstm_units": self.config.lstm_units,
                "dense_units": self.config.dense_units,
                "dropout_rate": self.config.dropout_rate,
                "activation": self.config.activation,
                "loss_weights": self.config.loss_weights,
            },
            "created_at": self.created_at.isoformat(),
            "training_metadata": self.training_metadata,
            "model_version": self.model_version,
        }

        with open(filepath, "w") as f:
            json.dump(metadata, f, indent=2)

    def _load_metadata(self, filepath: str) -> None:
        """메타데이터 로드"""
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                metadata = json.load(f)

            self.model_name = metadata.get("model_name", self.model_name)
            self.target_days = metadata.get("target_days", self.target_days)
            self.training_metadata = metadata.get("training_metadata", {})
            self.model_version = metadata.get("model_version")

            if "created_at" in metadata:
                self.created_at = datetime.fromisoformat(metadata["created_at"])

    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        info = {
            "model_name": self.model_name,
            "input_shape": self.input_shape,
            "target_days": self.target_days,
            "is_built": self.model is not None,
            "is_compiled": self.is_compiled,
            "created_at": self.created_at.isoformat(),
            "model_version": self.model_version,
            "config": {
                "lstm_units": self.config.lstm_units,
                "dense_units": self.config.dense_units,
                "dropout_rate": self.config.dropout_rate,
                "activation": self.config.activation,
                "loss_weights": self.config.loss_weights,
            },
        }

        if self.model is not None:
            info.update(
                {
                    "total_params": self.model.count_params(),
                    "trainable_params": sum(
                        [
                            tf.keras.backend.count_params(w)
                            for w in self.model.trainable_weights
                        ]
                    ),
                    "output_names": [output.name for output in self.model.outputs],
                }
            )

        if self.training_metadata:
            info["training_metadata"] = self.training_metadata

        return info

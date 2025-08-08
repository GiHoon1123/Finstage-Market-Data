"""
ML 예측 시스템 설정

이 파일은 딥러닝 모델 훈련 및 예측에 필요한 모든 설정값들을 정의합니다.
확장 가능한 구조로 설계되어 새로운 모델이나 데이터 소스 추가 시 쉽게 수정할 수 있습니다.
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import os


@dataclass
class ModelConfig:
    """
    LSTM 모델 아키텍처 설정

    멀티 아웃풋 LSTM 모델의 구조와 하이퍼파라미터를 정의합니다.
    7일, 14일, 30일 예측을 동시에 수행하는 모델 설정입니다.
    """

    # 입력 데이터 설정
    window_size: int = 60  # 과거 60일 데이터를 입력으로 사용
    target_days: List[int] = None  # 예측 대상 일수 [7, 14, 30]

    # LSTM 레이어 설정
    lstm_units: List[int] = None  # LSTM 유닛 수 [50, 50]
    dropout_rate: float = 0.2  # 과적합 방지를 위한 드롭아웃 비율

    # Dense 레이어 설정
    dense_units: List[int] = None  # Dense 레이어 유닛 수 [25]
    activation: str = "relu"  # 활성화 함수

    # 컴파일 설정
    optimizer: str = "adam"  # 최적화 알고리즘
    loss: str = "mse"  # 손실 함수 (Mean Squared Error)
    metrics: List[str] = None  # 평가 지표

    # 멀티 아웃풋 손실 가중치 (7일, 14일, 30일 순서)
    loss_weights: List[float] = None

    def __post_init__(self):
        """기본값 설정"""
        if self.target_days is None:
            self.target_days = [7, 14, 30]
        if self.lstm_units is None:
            self.lstm_units = [50, 50]
        if self.dense_units is None:
            self.dense_units = [25]
        if self.metrics is None:
            self.metrics = ["mae"]
        if self.loss_weights is None:
            # 단기 예측에 더 높은 가중치 (더 정확하기 때문)
            self.loss_weights = [0.5, 0.3, 0.2]


@dataclass
class DataConfig:
    """
    데이터 전처리 및 분할 설정

    시계열 데이터의 전처리, 정규화, 훈련/검증/테스트 분할 설정을 정의합니다.
    """

    # 데이터 분할 비율
    train_split: float = 0.7  # 70% 훈련용
    validation_split: float = 0.15  # 15% 검증용
    test_split: float = 0.15  # 15% 테스트용

    # 정규화 설정
    normalize_method: str = "minmax"  # 'minmax', 'standard', 'robust'
    feature_range: tuple = (0, 1)  # MinMaxScaler 범위

    # 결측치 처리
    handle_missing: str = "forward_fill"  # 'forward_fill', 'interpolate', 'drop'

    # 데이터 품질 검증
    min_data_points: int = 1000  # 최소 필요 데이터 포인트 수
    max_missing_ratio: float = 0.05  # 최대 허용 결측치 비율 (5%)

    # 특성 선택
    use_technical_indicators: bool = True  # 기술적 지표 사용 여부
    use_time_features: bool = True  # 시간 기반 특성 사용 여부
    use_volume_features: bool = True  # 거래량 특성 사용 여부


@dataclass
class TrainingConfig:
    """
    모델 훈련 설정

    배치 크기, 에포크 수, 조기 종료 등 훈련 과정의 설정을 정의합니다.
    """

    # 훈련 하이퍼파라미터
    batch_size: int = 32  # 배치 크기
    epochs: int = 100  # 최대 에포크 수
    learning_rate: float = 0.001  # 학습률

    # 조기 종료 설정
    early_stopping_patience: int = 10  # 성능 개선이 없을 때 대기할 에포크 수
    early_stopping_monitor: str = "val_loss"  # 모니터링할 지표
    early_stopping_mode: str = "min"  # 'min' (손실 최소화) 또는 'max' (정확도 최대화)

    # 모델 체크포인트 설정
    save_best_only: bool = True  # 최고 성능 모델만 저장
    save_weights_only: bool = False  # 전체 모델 저장 (가중치만이 아닌)

    # 학습률 스케줄링
    reduce_lr_patience: int = 5  # 학습률 감소 대기 에포크 수
    reduce_lr_factor: float = 0.5  # 학습률 감소 비율
    min_lr: float = 1e-7  # 최소 학습률


@dataclass
class PredictionConfig:
    """
    예측 실행 설정

    예측 수행 시 사용되는 설정값들을 정의합니다.
    """

    # 신뢰도 계산 설정
    confidence_method: str = "ensemble"  # 'ensemble', 'dropout', 'quantile'
    confidence_samples: int = 100  # 신뢰도 계산을 위한 샘플 수

    # 예측 일관성 검증
    consistency_threshold: float = 0.1  # 기간별 예측 일관성 임계값 (10%)

    # 배치 예측 설정
    max_batch_size: int = 1000  # 최대 배치 예측 크기

    # 결과 저장 설정
    save_predictions: bool = True  # 예측 결과 데이터베이스 저장 여부
    save_features: bool = True  # 사용된 특성 정보 저장 여부


@dataclass
class ModelStorageConfig:
    """
    모델 저장 및 버전 관리 설정

    훈련된 모델의 저장 경로, 버전 관리, 메타데이터 설정을 정의합니다.
    """

    # 저장 경로 설정
    base_model_path: str = "models/ml_prediction"  # 기본 모델 저장 경로
    model_format: str = "keras"  # 'keras', 'tensorflow', 'onnx'

    # 버전 관리
    version_format: str = "v{major}.{minor}.{patch}"  # 버전 형식
    auto_increment_version: bool = True  # 자동 버전 증가

    # 메타데이터 저장
    save_training_history: bool = True  # 훈련 이력 저장
    save_model_summary: bool = True  # 모델 구조 요약 저장
    save_hyperparameters: bool = True  # 하이퍼파라미터 저장

    # 모델 정리 설정
    max_model_versions: int = 10  # 최대 보관할 모델 버전 수
    auto_cleanup_old_models: bool = True  # 오래된 모델 자동 정리


# 전역 설정 인스턴스
DEFAULT_MODEL_CONFIG = ModelConfig()
DEFAULT_DATA_CONFIG = DataConfig()
DEFAULT_TRAINING_CONFIG = TrainingConfig()
DEFAULT_PREDICTION_CONFIG = PredictionConfig()
DEFAULT_STORAGE_CONFIG = ModelStorageConfig()


class MLSettings:
    """
    ML 예측 시스템 통합 설정 클래스

    모든 설정을 하나의 클래스로 통합하여 관리합니다.
    환경 변수를 통해 설정값을 오버라이드할 수 있습니다.
    """

    def __init__(self):
        self.model = DEFAULT_MODEL_CONFIG
        self.data = DEFAULT_DATA_CONFIG
        self.training = DEFAULT_TRAINING_CONFIG
        self.prediction = DEFAULT_PREDICTION_CONFIG
        self.storage = DEFAULT_STORAGE_CONFIG

        # 환경 변수로 설정 오버라이드
        self._load_from_env()

    def _load_from_env(self):
        """환경 변수에서 설정값 로드"""

        # 모델 설정 오버라이드
        if os.getenv("ML_WINDOW_SIZE"):
            self.model.window_size = int(os.getenv("ML_WINDOW_SIZE"))

        if os.getenv("ML_BATCH_SIZE"):
            self.training.batch_size = int(os.getenv("ML_BATCH_SIZE"))

        if os.getenv("ML_EPOCHS"):
            self.training.epochs = int(os.getenv("ML_EPOCHS"))

        if os.getenv("ML_LEARNING_RATE"):
            self.training.learning_rate = float(os.getenv("ML_LEARNING_RATE"))

        # 저장 경로 오버라이드
        if os.getenv("ML_MODEL_PATH"):
            self.storage.base_model_path = os.getenv("ML_MODEL_PATH")

    def get_model_save_path(self, model_name: str, version: str) -> str:
        """모델 저장 경로 생성"""
        return os.path.join(self.storage.base_model_path, model_name, version)

    def validate_config(self) -> List[str]:
        """설정값 검증"""
        errors = []

        # 데이터 분할 비율 검증
        total_split = (
            self.data.train_split + self.data.validation_split + self.data.test_split
        )
        if abs(total_split - 1.0) > 0.001:
            errors.append(f"데이터 분할 비율의 합이 1.0이 아닙니다: {total_split}")

        # 윈도우 크기 검증
        if self.model.window_size < max(self.model.target_days):
            errors.append(
                f"윈도우 크기({self.model.window_size})가 "
                f"최대 예측 일수({max(self.model.target_days)})보다 작습니다"
            )

        # 손실 가중치 검증
        if len(self.model.loss_weights) != len(self.model.target_days):
            errors.append(
                f"손실 가중치 개수({len(self.model.loss_weights)})가 "
                f"예측 일수 개수({len(self.model.target_days)})와 다릅니다"
            )

        return errors


# 전역 설정 인스턴스
ml_settings = MLSettings()


# 상수 정의
class MLConstants:
    """ML 시스템에서 사용되는 상수들"""

    # 지원하는 심볼
    SUPPORTED_SYMBOLS = ["^IXIC", "^GSPC"]

    # 예측 타임프레임
    TIMEFRAMES = ["7d", "14d", "30d"]

    # 모델 타입
    MODEL_TYPES = ["lstm", "gru", "transformer"]

    # 데이터 소스 타입
    DATA_SOURCE_TYPES = ["database", "api", "file", "web"]

    # 정규화 방법
    NORMALIZATION_METHODS = ["minmax", "standard", "robust"]

    # 신뢰도 계산 방법
    CONFIDENCE_METHODS = ["ensemble", "dropout", "quantile"]

    # 예측 방향
    PREDICTION_DIRECTIONS = ["up", "down", "neutral"]

    # 모델 상태
    MODEL_STATUS = ["training", "active", "deprecated", "failed"]

    # 에러 코드
    ERROR_CODES = {
        "MODEL_NOT_FOUND": "ML001",
        "INSUFFICIENT_DATA": "ML002",
        "TRAINING_FAILED": "ML003",
        "PREDICTION_FAILED": "ML004",
        "DATA_SOURCE_ERROR": "ML005",
        "INVALID_INPUT": "ML006",
        "MODEL_LOAD_ERROR": "ML007",
        "FEATURE_ENGINEERING_ERROR": "ML008",
    }


# 디렉토리 생성 함수
def ensure_directories():
    """필요한 디렉토리들을 생성합니다"""
    import os

    directories = [
        ml_settings.storage.base_model_path,
        os.path.join(ml_settings.storage.base_model_path, "checkpoints"),
        os.path.join(ml_settings.storage.base_model_path, "logs"),
        os.path.join(ml_settings.storage.base_model_path, "exports"),
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# 설정 검증 실행
if __name__ == "__main__":
    errors = ml_settings.validate_config()
    if errors:
        print("설정 검증 오류:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("모든 설정이 유효합니다.")
        ensure_directories()
        print("필요한 디렉토리가 생성되었습니다.")

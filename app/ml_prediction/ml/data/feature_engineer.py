"""
특성 엔지니어링 클래스

이 파일은 ML 예측 모델을 위한 특성 엔지니어링을 담당합니다.
시계열 데이터를 LSTM 모델에 적합한 형태로 변환하고,
멀티 타임프레임 예측을 위한 타겟 레이블을 생성합니다.

주요 기능:
- 멀티 타임프레임 시계열 윈도우 생성
- 특성 정규화 및 스케일링
- 타겟 레이블 생성 (7일, 14일, 30일)
- 시간 기반 특성 추가
"""

from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np

try:
    from sklearn.preprocessing import MinMaxScaler, StandardScaler, RobustScaler
    from sklearn.model_selection import train_test_split

    SKLEARN_AVAILABLE = True
except ImportError:
    # Fallback for sklearn import issues
    MinMaxScaler = None
    StandardScaler = None
    RobustScaler = None
    train_test_split = None
    SKLEARN_AVAILABLE = False
    StandardScaler = None
    RobustScaler = None
    train_test_split = None
import joblib
import os

from app.ml_prediction.config.ml_config import ml_settings
from app.common.utils.logging_config import get_logger
from app.ml_prediction.ml.data.sentiment_feature_engineer import SentimentFeatureEngineer

logger = get_logger(__name__)


class FeatureEngineer:
    """
    특성 엔지니어링 클래스

    시계열 데이터를 ML 모델에 적합한 형태로 변환합니다.
    멀티 타임프레임 예측을 위한 윈도우 생성과 타겟 레이블 생성을 지원합니다.
    """

    def __init__(
        self,
        window_size: int = None,
        target_days: List[int] = None,
        normalization_method: str = None,
    ):
        """
        특성 엔지니어 초기화

        Args:
            window_size: 시계열 윈도우 크기 (기본값: 설정에서 가져옴)
            target_days: 예측 대상 일수 목록 (기본값: [7, 14, 30])
            normalization_method: 정규화 방법 ('minmax', 'standard', 'robust')
        """
        self.window_size = window_size or ml_settings.model.window_size
        self.target_days = target_days or ml_settings.model.target_days
        self.normalization_method = (
            normalization_method or ml_settings.data.normalize_method
        )

        # 스케일러 저장
        self.feature_scaler = None
        self.target_scalers = {}  # 각 타임프레임별 스케일러

        # 특성 정보 저장
        self.feature_columns = []
        self.original_feature_count = 0
        self.engineered_feature_count = 0
        
        # 감정 특성 엔지니어 초기화
        self.sentiment_engineer = SentimentFeatureEngineer()
        self.use_sentiment_features = True  # 감정 특성 사용 여부

        logger.info(
            "feature_engineer_initialized",
            window_size=self.window_size,
            target_days=self.target_days,
            normalization_method=self.normalization_method,
        )

    def create_multi_target_sequences(
        self,
        data: pd.DataFrame,
        target_column: str = "close",
        include_features: bool = True,
        symbol: Optional[str] = None,
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray], List[str]]:
        """
        멀티 타임프레임 시계열 시퀀스 생성

        Args:
            data: 입력 데이터 (날짜 인덱스)
            target_column: 타겟 컬럼명
            include_features: 추가 특성 포함 여부
            symbol: 심볼 (감정분석 데이터 필터링용)

        Returns:
            (X: 특성 시퀀스, y: 타겟 딕셔너리, feature_names: 특성 이름 목록)
        """
        logger.info(
            "creating_multi_target_sequences",
            data_shape=data.shape,
            target_column=target_column,
            window_size=self.window_size,
            target_days=self.target_days,
            symbol=symbol,
        )

        if len(data) < self.window_size + max(self.target_days):
            raise ValueError(
                f"Insufficient data: need at least {self.window_size + max(self.target_days)} records, "
                f"got {len(data)}"
            )

        # 특성 준비
        if include_features:
            feature_data = self._prepare_features(data, symbol=symbol)
        else:
            feature_data = data[[target_column]].copy()

        self.feature_columns = feature_data.columns.tolist()
        self.original_feature_count = len(self.feature_columns)

        # 시계열 시퀀스 생성
        X, y_dict = self._create_sequences_and_targets(feature_data, target_column)

        logger.info(
            "multi_target_sequences_created",
            X_shape=X.shape,
            y_shapes={k: v.shape for k, v in y_dict.items()},
            feature_count=len(self.feature_columns),
            symbol=symbol,
        )

        return X, y_dict, self.feature_columns

    def _prepare_features(self, data: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        특성 데이터 준비 및 엔지니어링

        Args:
            data: 원본 데이터
            symbol: 심볼 (감정분석 데이터 필터링용)

        Returns:
            엔지니어링된 특성 데이터
        """
        feature_data = data.copy()

        # 1. 기본 가격 특성
        if all(col in feature_data.columns for col in ["open", "high", "low", "close"]):
            feature_data = self._add_price_features(feature_data)

        # 2. 거래량 특성
        if "volume" in feature_data.columns:
            feature_data = self._add_volume_features(feature_data)

        # 3. 기술적 지표 특성
        feature_data = self._add_technical_features(feature_data)

        # 4. 시간 기반 특성
        if ml_settings.data.use_time_features:
            feature_data = self._add_time_features(feature_data)

        # 5. 래그 특성
        feature_data = self._add_lag_features(feature_data)

        # 6. 롤링 통계 특성
        feature_data = self._add_rolling_features(feature_data)

        # 7. 감정 특성 추가 (심볼 정보 전달)
        feature_data = self._add_sentiment_features(feature_data, symbol=symbol)

        # 결측치 처리
        feature_data = self._handle_missing_values(feature_data)

        self.engineered_feature_count = len(feature_data.columns)

        logger.info(
            "features_prepared",
            symbol=symbol,
            original_features=self.original_feature_count,
            engineered_features=self.engineered_feature_count,
            added_features=self.engineered_feature_count - self.original_feature_count,
        )

        return feature_data

    def _add_price_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """가격 기반 특성 추가"""

        # 일일 수익률
        data["daily_return"] = data["close"].pct_change()

        # 가격 범위 (고가-저가)
        data["price_range"] = data["high"] - data["low"]
        data["price_range_pct"] = data["price_range"] / data["close"]

        # 캔들 몸통 크기
        data["candle_body"] = abs(data["close"] - data["open"])
        data["candle_body_pct"] = data["candle_body"] / data["close"]

        # 위꼬리, 아래꼬리
        data["upper_shadow"] = data["high"] - np.maximum(data["open"], data["close"])
        data["lower_shadow"] = np.minimum(data["open"], data["close"]) - data["low"]

        # 캔들 타입 (양봉/음봉)
        data["is_green_candle"] = (data["close"] > data["open"]).astype(float)

        # 갭 (전일 종가 대비 시가)
        data["gap"] = data["open"] - data["close"].shift(1)
        data["gap_pct"] = data["gap"] / data["close"].shift(1)

        return data

    def _add_volume_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """거래량 기반 특성 추가"""

        # 거래량 변화율
        data["volume_change"] = data["volume"].pct_change()

        # 가격-거래량 관계
        data["price_volume"] = data["close"] * data["volume"]

        # 거래량 가중 평균 가격 (VWAP 근사)
        data["vwap_approx"] = (data["high"] + data["low"] + data["close"]) / 3

        return data

    def _add_technical_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 특성 추가"""

        # 이동평균
        for period in [5, 10, 20, 50]:
            data[f"ma_{period}"] = data["close"].rolling(window=period).mean()
            data[f"ma_{period}_ratio"] = data["close"] / data[f"ma_{period}"]

        # RSI
        data["rsi"] = self._calculate_rsi(data["close"])

        # 볼린저 밴드
        bb_period = 20
        bb_std = 2
        data[f"bb_middle"] = data["close"].rolling(window=bb_period).mean()
        bb_std_val = data["close"].rolling(window=bb_period).std()
        data[f"bb_upper"] = data[f"bb_middle"] + (bb_std_val * bb_std)
        data[f"bb_lower"] = data[f"bb_middle"] - (bb_std_val * bb_std)
        data["bb_position"] = (data["close"] - data[f"bb_lower"]) / (
            data[f"bb_upper"] - data[f"bb_lower"]
        )

        # MACD
        ema_12 = data["close"].ewm(span=12).mean()
        ema_26 = data["close"].ewm(span=26).mean()
        data["macd"] = ema_12 - ema_26
        data["macd_signal"] = data["macd"].ewm(span=9).mean()
        data["macd_histogram"] = data["macd"] - data["macd_signal"]

        return data

    def _add_time_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """시간 기반 특성 추가"""

        # 인덱스를 DatetimeIndex로 변환 (필요한 경우)
        if not isinstance(data.index, pd.DatetimeIndex):
            if "date" in data.columns:
                data = data.set_index("date")
                data.index = pd.to_datetime(data.index)
            else:
                # 인덱스가 날짜가 아닌 경우 기본 시간 특성 추가 불가
                logger.warning(
                    "Cannot add time features: index is not DatetimeIndex and no 'date' column found"
                )
                return data

        # 요일 (0=월요일, 6=일요일)
        data["day_of_week"] = data.index.weekday

        # 월
        data["month"] = data.index.month

        # 분기
        data["quarter"] = data.index.quarter

        # 월 시작/끝 여부
        data["is_month_start"] = data.index.is_month_start.astype(float)
        data["is_month_end"] = data.index.is_month_end.astype(float)

        # 분기 시작/끝 여부
        data["is_quarter_start"] = data.index.is_quarter_start.astype(float)
        data["is_quarter_end"] = data.index.is_quarter_end.astype(float)

        # 요일별 원-핫 인코딩
        for i in range(7):
            data[f"is_weekday_{i}"] = (data.index.weekday == i).astype(float)

        return data

    def _add_lag_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """래그 특성 추가"""

        # 주요 컬럼들의 래그 특성
        lag_columns = ["close", "volume", "daily_return"]
        lag_periods = [1, 2, 3, 5, 10]

        for col in lag_columns:
            if col in data.columns:
                for lag in lag_periods:
                    data[f"{col}_lag_{lag}"] = data[col].shift(lag)

        return data

    def _add_rolling_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """롤링 통계 특성 추가"""

        # 롤링 윈도우 크기들
        windows = [5, 10, 20]

        for window in windows:
            # 가격 롤링 통계
            data[f"close_mean_{window}"] = data["close"].rolling(window=window).mean()
            data[f"close_std_{window}"] = data["close"].rolling(window=window).std()
            data[f"close_min_{window}"] = data["close"].rolling(window=window).min()
            data[f"close_max_{window}"] = data["close"].rolling(window=window).max()

            # 거래량 롤링 통계
            if "volume" in data.columns:
                data[f"volume_mean_{window}"] = (
                    data["volume"].rolling(window=window).mean()
                )
                data[f"volume_std_{window}"] = (
                    data["volume"].rolling(window=window).std()
                )

            # 수익률 롤링 통계
            if "daily_return" in data.columns:
                data[f"return_mean_{window}"] = (
                    data["daily_return"].rolling(window=window).mean()
                )
                data[f"return_std_{window}"] = (
                    data["daily_return"].rolling(window=window).std()
                )

        return data

    def _add_sentiment_features(self, data: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        """감정 특성 추가"""
        
        if not self.use_sentiment_features:
            logger.info("sentiment_features_disabled")
            return data
        
        try:
            # 데이터의 날짜 범위 확인
            start_date = data.index.min()
            end_date = data.index.max()
            
            # 감정 특성 생성
            sentiment_features = self.sentiment_engineer.get_sentiment_features(
                start_date=start_date,
                end_date=end_date,
                symbol=symbol
            )
            
            # 가격 데이터와 감정 데이터 병합
            data_with_sentiment = self.sentiment_engineer.merge_with_price_data(
                price_df=data,
                sentiment_df=sentiment_features
            )
            
            # 감정 특성 컬럼명을 일관되게 저장 (순서 유지)
            sentiment_columns = self.sentiment_engineer.get_feature_names()
            
            # 기존 특성 컬럼에서 감정 특성 제거 후 다시 추가 (순서 보장)
            self.feature_columns = [col for col in self.feature_columns if col not in sentiment_columns]
            self.feature_columns.extend(sentiment_columns)
            
            logger.info(
                "sentiment_features_added",
                symbol=symbol,
                sentiment_features=len(sentiment_columns),
                total_features=len(data_with_sentiment.columns)
            )
            
            return data_with_sentiment
            
        except Exception as e:
            logger.error("sentiment_features_add_failed", error=str(e), symbol=symbol)
            return data

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _handle_missing_values(self, data: pd.DataFrame) -> pd.DataFrame:
        """결측치 처리"""

        # 전진 채움 후 후진 채움
        data = data.fillna(method="ffill").fillna(method="bfill")

        # 여전히 결측치가 있는 경우 0으로 채움
        data = data.fillna(0)

        return data

    def _create_sequences_and_targets(
        self, feature_data: pd.DataFrame, target_column: str
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """
        시계열 시퀀스와 멀티 타겟 생성

        Args:
            feature_data: 특성 데이터
            target_column: 타겟 컬럼명

        Returns:
            (X: 특성 시퀀스, y_dict: 타겟 딕셔너리)
        """
        X = []
        y_dict = {f"{days}d": [] for days in self.target_days}

        # 최대 예측 일수만큼 여유를 둠
        max_target_days = max(self.target_days)

        for i in range(self.window_size, len(feature_data) - max_target_days):
            # 특성 시퀀스 (과거 window_size일)
            X.append(feature_data.iloc[i - self.window_size : i].values)

            # 각 타임프레임별 타겟
            for days in self.target_days:
                future_price = feature_data.iloc[i + days][target_column]
                y_dict[f"{days}d"].append(future_price)

        # numpy 배열로 변환
        X = np.array(X)
        for key in y_dict:
            y_dict[key] = np.array(y_dict[key])

        return X, y_dict

    def normalize_features(self, X: np.ndarray, fit_scaler: bool = True) -> np.ndarray:
        """
        특성 정규화

        Args:
            X: 특성 데이터
            fit_scaler: 스케일러 학습 여부

        Returns:
            정규화된 특성 데이터
        """
        if fit_scaler or self.feature_scaler is None:
            # 스케일러 생성
            if self.normalization_method == "minmax":
                self.feature_scaler = MinMaxScaler(
                    feature_range=ml_settings.data.feature_range
                )
            elif self.normalization_method == "standard":
                self.feature_scaler = StandardScaler()
            elif self.normalization_method == "robust":
                self.feature_scaler = RobustScaler()
            else:
                raise ValueError(
                    f"Unknown normalization method: {self.normalization_method}"
                )

            # 3D 데이터를 2D로 변환하여 스케일러 학습
            original_shape = X.shape
            X_2d = X.reshape(-1, X.shape[-1])

            # 스케일러 학습 및 변환
            X_normalized_2d = self.feature_scaler.fit_transform(X_2d)

            # 원래 3D 형태로 복원
            X_normalized = X_normalized_2d.reshape(original_shape)

            logger.info(
                "feature_scaler_fitted",
                normalization_method=self.normalization_method,
                input_shape=original_shape,
                feature_range=getattr(self.feature_scaler, "feature_range", "N/A"),
            )
        else:
            # 기존 스케일러로 변환만
            original_shape = X.shape
            X_2d = X.reshape(-1, X.shape[-1])
            X_normalized_2d = self.feature_scaler.transform(X_2d)
            X_normalized = X_normalized_2d.reshape(original_shape)

        return X_normalized

    def normalize_targets(
        self, y_dict: Dict[str, np.ndarray], fit_scalers: bool = True
    ) -> Dict[str, np.ndarray]:
        """
        타겟 정규화

        Args:
            y_dict: 타겟 딕셔너리
            fit_scalers: 스케일러 학습 여부

        Returns:
            정규화된 타겟 딕셔너리
        """
        normalized_y_dict = {}

        for timeframe, y in y_dict.items():
            if fit_scalers or timeframe not in self.target_scalers:
                # 타겟별 스케일러 생성
                if self.normalization_method == "minmax":
                    scaler = MinMaxScaler(feature_range=ml_settings.data.feature_range)
                elif self.normalization_method == "standard":
                    scaler = StandardScaler()
                elif self.normalization_method == "robust":
                    scaler = RobustScaler()
                else:
                    raise ValueError(
                        f"Unknown normalization method: {self.normalization_method}"
                    )

                # 1D 데이터를 2D로 변환하여 스케일러 학습
                y_2d = y.reshape(-1, 1)
                y_normalized_2d = scaler.fit_transform(y_2d)
                y_normalized = y_normalized_2d.flatten()

                self.target_scalers[timeframe] = scaler

                logger.debug(
                    "target_scaler_fitted",
                    timeframe=timeframe,
                    original_range=(y.min(), y.max()),
                    normalized_range=(y_normalized.min(), y_normalized.max()),
                )
            else:
                # 기존 스케일러로 변환만
                y_2d = y.reshape(-1, 1)
                y_normalized_2d = self.target_scalers[timeframe].transform(y_2d)
                y_normalized = y_normalized_2d.flatten()

            normalized_y_dict[timeframe] = y_normalized

        return normalized_y_dict

    def denormalize_predictions(
        self, predictions_dict: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        예측 결과 역정규화

        Args:
            predictions_dict: 정규화된 예측 결과

        Returns:
            역정규화된 예측 결과
        """
        denormalized_dict = {}

        for timeframe, predictions in predictions_dict.items():
            if timeframe in self.target_scalers:
                predictions_2d = predictions.reshape(-1, 1)
                denormalized_2d = self.target_scalers[timeframe].inverse_transform(
                    predictions_2d
                )
                denormalized_dict[timeframe] = denormalized_2d.flatten()
            else:
                logger.warning("target_scaler_not_found", timeframe=timeframe)
                denormalized_dict[timeframe] = predictions

        return denormalized_dict

    def split_data(
        self,
        X: np.ndarray,
        y_dict: Dict[str, np.ndarray],
        train_ratio: float = None,
        val_ratio: float = None,
        test_ratio: float = None,
        shuffle: bool = False,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Dict[str, np.ndarray]]]:
        """
        데이터 분할 (시계열 순서 고려)

        Args:
            X: 특성 데이터
            y_dict: 타겟 딕셔너리
            train_ratio: 훈련 데이터 비율
            val_ratio: 검증 데이터 비율
            test_ratio: 테스트 데이터 비율
            shuffle: 셔플 여부 (시계열에서는 False 권장)

        Returns:
            (X_splits, y_splits) 튜플
        """
        train_ratio = train_ratio or ml_settings.data.train_split
        val_ratio = val_ratio or ml_settings.data.validation_split
        test_ratio = test_ratio or ml_settings.data.test_split

        # 비율 검증
        if abs(train_ratio + val_ratio + test_ratio - 1.0) > 0.001:
            raise ValueError("Split ratios must sum to 1.0")

        n_samples = len(X)

        if shuffle:
            # 셔플 분할 (일반적인 ML에서 사용)
            indices = np.arange(n_samples)
            train_indices, temp_indices = train_test_split(
                indices, train_size=train_ratio, random_state=42
            )
            val_indices, test_indices = train_test_split(
                temp_indices,
                train_size=val_ratio / (val_ratio + test_ratio),
                random_state=42,
            )
        else:
            # 시계열 순서 유지 분할
            train_end = int(n_samples * train_ratio)
            val_end = int(n_samples * (train_ratio + val_ratio))

            train_indices = np.arange(0, train_end)
            val_indices = np.arange(train_end, val_end)
            test_indices = np.arange(val_end, n_samples)

        # X 분할
        X_splits = {
            "train": X[train_indices],
            "val": X[val_indices],
            "test": X[test_indices],
        }

        # y 분할
        y_splits = {}
        for timeframe, y in y_dict.items():
            y_splits[timeframe] = {
                "train": y[train_indices],
                "val": y[val_indices],
                "test": y[test_indices],
            }

        logger.info(
            "data_split_completed",
            total_samples=n_samples,
            train_samples=len(train_indices),
            val_samples=len(val_indices),
            test_samples=len(test_indices),
            shuffle=shuffle,
        )

        return X_splits, y_splits

    def save_scalers(self, save_dir: str) -> None:
        """스케일러 저장"""
        os.makedirs(save_dir, exist_ok=True)

        # 특성 스케일러 저장
        if self.feature_scaler is not None:
            feature_scaler_path = os.path.join(save_dir, "feature_scaler.pkl")
            joblib.dump(self.feature_scaler, feature_scaler_path)

            logger.info("feature_scaler_saved", path=feature_scaler_path)

        # 타겟 스케일러들 저장
        for timeframe, scaler in self.target_scalers.items():
            target_scaler_path = os.path.join(
                save_dir, f"target_scaler_{timeframe}.pkl"
            )
            joblib.dump(scaler, target_scaler_path)

            logger.debug(
                "target_scaler_saved", timeframe=timeframe, path=target_scaler_path
            )

    def load_scalers(self, save_dir: str) -> None:
        """스케일러 로드"""

        # 특성 스케일러 로드
        feature_scaler_path = os.path.join(save_dir, "feature_scaler.pkl")
        if os.path.exists(feature_scaler_path):
            self.feature_scaler = joblib.load(feature_scaler_path)
            logger.info("feature_scaler_loaded", path=feature_scaler_path)

        # 타겟 스케일러들 로드
        for timeframe in self.target_days:
            timeframe_str = f"{timeframe}d"
            target_scaler_path = os.path.join(
                save_dir, f"target_scaler_{timeframe_str}.pkl"
            )

            if os.path.exists(target_scaler_path):
                self.target_scalers[timeframe_str] = joblib.load(target_scaler_path)
                logger.debug(
                    "target_scaler_loaded",
                    timeframe=timeframe_str,
                    path=target_scaler_path,
                )

    def get_feature_info(self) -> Dict[str, Any]:
        """특성 정보 반환"""
        return {
            "window_size": self.window_size,
            "target_days": self.target_days,
            "normalization_method": self.normalization_method,
            "feature_columns": self.feature_columns,
            "original_feature_count": self.original_feature_count,
            "engineered_feature_count": self.engineered_feature_count,
            "has_feature_scaler": self.feature_scaler is not None,
            "target_scalers": list(self.target_scalers.keys()),
        }

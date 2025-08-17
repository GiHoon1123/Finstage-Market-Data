"""
데이터 전처리기

이 파일은 ML 예측 시스템의 전체 데이터 전처리 파이프라인을 관리합니다.
데이터 소스 통합, 특성 엔지니어링, 품질 검증을 하나의 워크플로우로 제공합니다.

주요 기능:
- 통합 데이터 전처리 파이프라인
- 기술적 지표 특성 변환
- 데이터 품질 검증 및 정리
- 캐싱 및 성능 최적화
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import pandas as pd
import numpy as np
import time
import hashlib
import pickle
import os

from app.ml_prediction.ml.data.source_manager import DataSourceManager
from app.ml_prediction.ml.data.feature_engineer import FeatureEngineer
from app.ml_prediction.ml.data.quality_validator import (
    DataQualityValidator,
    ValidationSeverity,
)
from app.ml_prediction.ml.data.fallback_handler import DataSourceFallbackHandler
from app.ml_prediction.config.ml_config import ml_settings
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class MLDataPreprocessor:
    """
    ML 데이터 전처리기

    데이터 수집부터 모델 입력 준비까지의 전체 파이프라인을 관리합니다.
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        enable_caching: bool = True,
        strict_validation: bool = False,
    ):
        """
        전처리기 초기화

        Args:
            cache_dir: 캐시 디렉토리
            enable_caching: 캐싱 활성화 여부
            strict_validation: 엄격한 검증 모드
        """
        self.cache_dir = cache_dir or os.path.join(
            ml_settings.storage.base_model_path, "cache"
        )
        self.enable_caching = enable_caching
        self.strict_validation = strict_validation

        # 컴포넌트 초기화
        self.data_source_manager = DataSourceManager()
        self.feature_engineer = FeatureEngineer()
        self.quality_validator = DataQualityValidator(strict_mode=strict_validation)
        self.fallback_handler = DataSourceFallbackHandler()

        # 캐시 디렉토리 생성
        if self.enable_caching:
            os.makedirs(self.cache_dir, exist_ok=True)

        logger.info(
            "ml_data_preprocessor_initialized",
            cache_dir=self.cache_dir,
            enable_caching=enable_caching,
            strict_validation=strict_validation,
        )

    def prepare_training_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        target_column: str = "close",
        force_refresh: bool = False,
        use_sentiment: bool = False,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Dict[str, np.ndarray]], Dict[str, Any]]:
        """
        훈련 데이터 준비

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            target_column: 타겟 컬럼명
            force_refresh: 캐시 무시하고 새로 생성

        Returns:
            (X_splits, y_splits, metadata) 튜플
        """
        start_time = time.time()

        logger.info(
            "training_data_preparation_started",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            target_column=target_column,
        )

        # 1. 캐시 확인
        if self.enable_caching and not force_refresh:
            cached_data = self._load_from_cache(
                symbol, start_date, end_date, "training"
            )
            if cached_data is not None:
                logger.info("training_data_loaded_from_cache")
                return cached_data

        # 2. 원시 데이터 수집
        raw_data = self._collect_raw_data(symbol, start_date, end_date)

        # 3. 데이터 품질 검증
        validation_passed, validation_results, quality_score = (
            self._validate_data_quality(raw_data, symbol, (start_date, end_date))
        )

        if not validation_passed:
            raise ValueError(f"Data quality validation failed for {symbol}")

        # 4. 특성 엔지니어링
        # 감정 특성 사용 설정
        if use_sentiment:
            self.feature_engineer.use_sentiment_features = True
            logger.info("sentiment_features_enabled_for_training", symbol=symbol)
        
        X, y_dict, feature_names = self.feature_engineer.create_multi_target_sequences(
            raw_data, target_column=target_column, symbol=symbol
        )

        # 5. 정규화
        X_normalized = self.feature_engineer.normalize_features(X, fit_scaler=True)
        y_normalized_dict = self.feature_engineer.normalize_targets(
            y_dict, fit_scalers=True
        )

        # 6. 데이터 분할
        X_splits, y_splits = self.feature_engineer.split_data(
            X_normalized, y_normalized_dict
        )

        # 7. 메타데이터 생성
        metadata = self._create_metadata(
            symbol,
            start_date,
            end_date,
            raw_data,
            validation_results,
            quality_score,
            feature_names,
        )

        # 8. 캐시 저장
        if self.enable_caching:
            self._save_to_cache(
                (X_splits, y_splits, metadata), symbol, start_date, end_date, "training"
            )

        elapsed_time = time.time() - start_time

        logger.info(
            "training_data_preparation_completed",
            symbol=symbol,
            elapsed_seconds=round(elapsed_time, 2),
            train_samples=len(X_splits["train"]),
            val_samples=len(X_splits["val"]),
            test_samples=len(X_splits["test"]),
            features=len(feature_names),
            quality_score=quality_score.overall_score,
        )

        return X_splits, y_splits, metadata

    def prepare_prediction_data(
        self, symbol: str, end_date: date, lookback_days: int = None, use_sentiment: bool = False
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        예측용 데이터 준비

        Args:
            symbol: 심볼
            end_date: 마지막 날짜
            lookback_days: 과거 며칠 데이터 사용
            use_sentiment: 감정분석 특성 사용 여부

        Returns:
            (X: 예측용 특성, metadata: 메타데이터) 튜플
        """
        lookback_days = lookback_days or (self.feature_engineer.window_size + 30)
        start_date = end_date - timedelta(days=lookback_days)

        logger.info(
            "prediction_data_preparation_started",
            symbol=symbol,
            end_date=end_date,
            lookback_days=lookback_days,
            use_sentiment=use_sentiment,
        )

        # 1. 원시 데이터 수집
        raw_data = self._collect_raw_data(symbol, start_date, end_date)

        # 2. 특성 엔지니어링 (타겟 없이, 심볼 정보 전달)
        feature_data = self.feature_engineer._prepare_features(raw_data, symbol=symbol)

        # 최근 window_size만큼의 데이터로 시퀀스 생성
        if len(feature_data) < self.feature_engineer.window_size:
            raise ValueError(
                f"Insufficient data for prediction: need {self.feature_engineer.window_size} records, "
                f"got {len(feature_data)}"
            )

        # 마지막 윈도우 추출
        X = feature_data.iloc[-self.feature_engineer.window_size :].values
        X = X.reshape(
            1, self.feature_engineer.window_size, -1
        )  # (1, window_size, features)

        # 4. 정규화 (기존 스케일러 사용)
        if self.feature_engineer.feature_scaler is None:
            # 스케일러가 로드되지 않은 경우, 모델에서 스케일러를 로드
            logger.warning("feature_scaler_not_loaded_trying_to_load_from_model", symbol=symbol)
            
            # 모델 경로에서 스케일러 로드 시도
            try:
                from app.ml_prediction.infra.model.repository.ml_model_repository import MLModelRepository
                from app.common.infra.database.config.database_config import SessionLocal
                
                session = SessionLocal()
                model_repository = MLModelRepository(session)
                
                # 활성 모델 조회
                model_entity = model_repository.find_active_model("lstm", symbol)
                
                if model_entity:
                    # 스케일러 디렉토리 경로
                    scaler_dir = os.path.join(os.path.dirname(model_entity.model_path), "scalers")
                    if os.path.exists(scaler_dir):
                        self.feature_engineer.load_scalers(scaler_dir)
                        logger.info("feature_scaler_loaded_from_model", symbol=symbol, scaler_dir=scaler_dir)
                    else:
                        raise ValueError(f"Scaler directory not found: {scaler_dir}")
                else:
                    raise ValueError(f"No active model found for {symbol}")
                    
                session.close()
                
            except Exception as e:
                logger.error("failed_to_load_scaler_from_model", symbol=symbol, error=str(e))
                raise ValueError(f"Feature scaler not fitted and failed to load from model. Train model first. Error: {str(e)}")

        X_normalized = self.feature_engineer.normalize_features(X, fit_scaler=False)

        # 5. 메타데이터
        metadata = {
            "symbol": symbol,
            "end_date": end_date.isoformat(),
            "lookback_days": lookback_days,
            "data_points": len(raw_data),
            "feature_count": X.shape[-1],
            "last_price": float(raw_data["close"].iloc[-1]),
            "data_date_range": {
                "start": str(raw_data.index.min()),
                "end": str(raw_data.index.max()),
            },
            "sentiment_features_enabled": self.feature_engineer.use_sentiment_features,
        }

        logger.info(
            "prediction_data_preparation_completed",
            symbol=symbol,
            features=X.shape[-1],
            last_price=metadata["last_price"],
            sentiment_features_enabled=self.feature_engineer.use_sentiment_features,
        )

        return X_normalized, metadata

    def _collect_raw_data(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        원시 데이터 수집 (폴백 처리 포함)

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            수집된 원시 데이터
        """
        try:
            # 데이터 소스 매니저를 통해 데이터 수집
            raw_data = self.data_source_manager.fetch_all_data(
                symbol, start_date, end_date, parallel=True
            )

            if raw_data.empty:
                raise ValueError(f"No data collected for {symbol}")

            # 데이터 소스 매니저의 통합 검증
            is_valid, errors = self.data_source_manager.validate_combined_data(raw_data)

            if not is_valid:
                logger.warning(
                    "raw_data_validation_issues", symbol=symbol, errors=errors
                )

                # 폴백 핸들러를 통해 데이터 복구 시도
                # (여기서는 간단히 경고만 로그)

            return raw_data

        except Exception as e:
            logger.error(
                "raw_data_collection_failed",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                error=str(e),
            )
            raise

    def _validate_data_quality(
        self, data: pd.DataFrame, symbol: str, expected_date_range: Tuple[date, date]
    ) -> Tuple[bool, List, Any]:
        """
        데이터 품질 검증

        Args:
            data: 검증할 데이터
            symbol: 심볼
            expected_date_range: 예상 날짜 범위

        Returns:
            (검증 통과 여부, 검증 결과, 품질 점수)
        """
        required_columns = ["open", "high", "low", "close"]

        validation_passed, validation_results, quality_score = (
            self.quality_validator.validate_dataset(
                data, symbol, expected_date_range, required_columns
            )
        )

        # 심각한 오류가 있는 경우 로그
        critical_errors = [
            r for r in validation_results if r.severity == ValidationSeverity.CRITICAL
        ]

        if critical_errors:
            for error in critical_errors:
                logger.error(
                    "critical_data_quality_issue",
                    symbol=symbol,
                    check=error.check_name,
                    message=error.message,
                )

        return validation_passed, validation_results, quality_score

    def _create_metadata(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        raw_data: pd.DataFrame,
        validation_results: List,
        quality_score: Any,
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """메타데이터 생성"""

        return {
            "symbol": symbol,
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "raw_data_info": {
                "records": len(raw_data),
                "columns": len(raw_data.columns),
                "date_range": {
                    "start": str(raw_data.index.min()),
                    "end": str(raw_data.index.max()),
                },
            },
            "feature_engineering": {
                "window_size": self.feature_engineer.window_size,
                "target_days": self.feature_engineer.target_days,
                "feature_count": len(feature_names),
                "feature_names": feature_names,
                "normalization_method": self.feature_engineer.normalization_method,
            },
            "data_quality": {
                "overall_score": quality_score.overall_score,
                "completeness_score": quality_score.completeness_score,
                "consistency_score": quality_score.consistency_score,
                "accuracy_score": quality_score.accuracy_score,
                "validation_summary": self.quality_validator.get_validation_summary(),
            },
            "preprocessing_config": {
                "cache_enabled": self.enable_caching,
                "strict_validation": self.strict_validation,
            },
            "created_at": datetime.now().isoformat(),
        }

    def _generate_cache_key(
        self, symbol: str, start_date: date, end_date: date, data_type: str
    ) -> str:
        """캐시 키 생성"""
        key_data = f"{symbol}:{start_date}:{end_date}:{data_type}:{self.feature_engineer.window_size}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _save_to_cache(
        self, data: Any, symbol: str, start_date: date, end_date: date, data_type: str
    ) -> None:
        """캐시에 데이터 저장"""
        if not self.enable_caching:
            return

        try:
            cache_key = self._generate_cache_key(
                symbol, start_date, end_date, data_type
            )
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

            cache_data = {
                "data": data,
                "metadata": {
                    "symbol": symbol,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "data_type": data_type,
                    "created_at": datetime.now().isoformat(),
                    "feature_engineer_config": self.feature_engineer.get_feature_info(),
                },
            }

            with open(cache_file, "wb") as f:
                pickle.dump(cache_data, f)

            logger.debug(
                "data_cached", symbol=symbol, data_type=data_type, cache_file=cache_file
            )

        except Exception as e:
            logger.error(
                "cache_save_failed", symbol=symbol, data_type=data_type, error=str(e)
            )

    def _load_from_cache(
        self, symbol: str, start_date: date, end_date: date, data_type: str
    ) -> Optional[Any]:
        """캐시에서 데이터 로드"""
        if not self.enable_caching:
            return None

        try:
            cache_key = self._generate_cache_key(
                symbol, start_date, end_date, data_type
            )
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

            if not os.path.exists(cache_file):
                return None

            # 캐시 파일 나이 확인
            file_age = datetime.now() - datetime.fromtimestamp(
                os.path.getmtime(cache_file)
            )
            if file_age > timedelta(hours=24):  # 24시간 이상 된 캐시는 무효
                os.remove(cache_file)
                logger.debug("expired_cache_removed", cache_file=cache_file)
                return None

            with open(cache_file, "rb") as f:
                cache_data = pickle.load(f)

            # 설정 호환성 확인
            cached_config = cache_data["metadata"].get("feature_engineer_config", {})
            current_config = self.feature_engineer.get_feature_info()

            if cached_config.get("window_size") != current_config.get(
                "window_size"
            ) or cached_config.get("target_days") != current_config.get("target_days"):
                logger.debug("cache_config_mismatch", cache_file=cache_file)
                return None

            logger.debug(
                "data_loaded_from_cache",
                symbol=symbol,
                data_type=data_type,
                cache_file=cache_file,
            )

            return cache_data["data"]

        except Exception as e:
            logger.error(
                "cache_load_failed", symbol=symbol, data_type=data_type, error=str(e)
            )
            return None

    def clear_cache(self, symbol: Optional[str] = None) -> int:
        """
        캐시 정리

        Args:
            symbol: 특정 심볼의 캐시만 정리 (None이면 전체)

        Returns:
            정리된 파일 수
        """
        if not self.enable_caching or not os.path.exists(self.cache_dir):
            return 0

        cleared_count = 0

        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".pkl"):
                    filepath = os.path.join(self.cache_dir, filename)

                    if symbol is None:
                        # 전체 캐시 정리
                        os.remove(filepath)
                        cleared_count += 1
                    else:
                        # 특정 심볼 캐시만 정리 (파일명에서 확인)
                        try:
                            with open(filepath, "rb") as f:
                                cache_data = pickle.load(f)

                            if cache_data["metadata"].get("symbol") == symbol:
                                os.remove(filepath)
                                cleared_count += 1
                        except:
                            # 손상된 캐시 파일은 삭제
                            os.remove(filepath)
                            cleared_count += 1

            logger.info(
                "cache_cleared", symbol=symbol or "all", cleared_files=cleared_count
            )

        except Exception as e:
            logger.error("cache_clear_failed", error=str(e))

        return cleared_count

    def get_preprocessing_stats(self) -> Dict[str, Any]:
        """전처리 통계 정보 반환"""

        cache_stats = {"enabled": False, "files": 0, "size_mb": 0}

        if self.enable_caching and os.path.exists(self.cache_dir):
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith(".pkl")]
            cache_stats["enabled"] = True
            cache_stats["files"] = len(cache_files)

            # 캐시 크기 계산
            total_size = 0
            for filename in cache_files:
                filepath = os.path.join(self.cache_dir, filename)
                total_size += os.path.getsize(filepath)
            cache_stats["size_mb"] = round(total_size / (1024 * 1024), 2)

        return {
            "data_source_manager": self.data_source_manager.health_check(),
            "feature_engineer": self.feature_engineer.get_feature_info(),
            "fallback_handler": self.fallback_handler.get_fallback_statistics(),
            "cache_stats": cache_stats,
            "config": {
                "cache_dir": self.cache_dir,
                "enable_caching": self.enable_caching,
                "strict_validation": self.strict_validation,
            },
        }

"""
데이터 소스 관리자

이 파일은 여러 데이터 소스를 통합 관리하는 매니저 클래스를 정의합니다.
플러그인 방식으로 데이터 소스를 등록하고, 우선순위에 따라 데이터를 수집하며,
오류 발생 시 폴백 메커니즘을 제공합니다.

주요 기능:
- 다중 데이터 소스 통합 관리
- 우선순위 기반 데이터 수집
- 오류 발생 시 폴백 처리
- 데이터 품질 검증 및 통합
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.ml_prediction.ml.data.data_source import (
    DataSource,
    DatabasePriceDataSource,
    DatabaseTechnicalDataSource,
    TimeBasedFeatureSource,
)
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class DataSourceManager:
    """
    데이터 소스 통합 관리자

    여러 데이터 소스를 등록하고 관리하며, 우선순위에 따라 데이터를 수집합니다.
    오류 발생 시 다른 소스로 폴백하는 메커니즘을 제공합니다.
    """

    def __init__(self, max_workers: int = 3, timeout_seconds: int = 30):
        """
        데이터 소스 관리자 초기화

        Args:
            max_workers: 병렬 처리 최대 워커 수
            timeout_seconds: 데이터 수집 타임아웃 (초)
        """
        self.sources: Dict[str, DataSource] = {}
        self.max_workers = max_workers
        self.timeout_seconds = timeout_seconds

        # 기본 데이터 소스들 등록
        self._register_default_sources()

    def _register_default_sources(self) -> None:
        """기본 데이터 소스들을 등록합니다"""
        try:
            # 데이터베이스 가격 데이터 소스
            price_source = DatabasePriceDataSource()
            self.register_source(price_source)

            # 데이터베이스 기술적 지표 소스
            technical_source = DatabaseTechnicalDataSource()
            self.register_source(technical_source)

            # 시간 기반 특성 소스
            time_source = TimeBasedFeatureSource()
            self.register_source(time_source)

            logger.info(
                "default_data_sources_registered",
                sources=[source.name for source in self.sources.values()],
            )

        except Exception as e:
            logger.error("failed_to_register_default_sources", error=str(e))

    def register_source(self, source: DataSource) -> bool:
        """
        새로운 데이터 소스 등록

        Args:
            source: 등록할 데이터 소스

        Returns:
            등록 성공 여부
        """
        try:
            if source.name in self.sources:
                logger.warning(
                    "data_source_already_registered", source_name=source.name
                )
                return False

            self.sources[source.name] = source

            logger.info(
                "data_source_registered",
                source_name=source.name,
                priority=source.priority,
                feature_columns=len(source.get_feature_columns()),
            )

            return True

        except Exception as e:
            logger.error(
                "data_source_registration_failed",
                source_name=source.name if hasattr(source, "name") else "unknown",
                error=str(e),
            )
            return False

    def unregister_source(self, source_name: str) -> bool:
        """
        데이터 소스 등록 해제

        Args:
            source_name: 해제할 데이터 소스 이름

        Returns:
            해제 성공 여부
        """
        if source_name not in self.sources:
            logger.warning(
                "data_source_not_found_for_unregister", source_name=source_name
            )
            return False

        del self.sources[source_name]

        logger.info("data_source_unregistered", source_name=source_name)

        return True

    def get_available_sources(self) -> List[DataSource]:
        """
        사용 가능한 데이터 소스 목록 반환 (우선순위 순)

        Returns:
            사용 가능한 데이터 소스 목록
        """
        available_sources = [
            source for source in self.sources.values() if source.is_available()
        ]

        # 우선순위 순으로 정렬
        available_sources.sort(key=lambda x: x.priority)

        return available_sources

    def get_all_feature_names(self) -> List[str]:
        """
        모든 등록된 소스의 특성 이름 목록 반환

        Returns:
            전체 특성 이름 목록
        """
        all_features = []

        for source in self.sources.values():
            if source.is_available():
                features = source.get_feature_columns()
                all_features.extend(features)

        # 중복 제거 및 정렬
        return sorted(list(set(all_features)))

    def fetch_all_data(
        self, symbol: str, start_date: date, end_date: date, parallel: bool = True
    ) -> pd.DataFrame:
        """
        모든 등록된 소스에서 데이터 수집 및 통합

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            parallel: 병렬 처리 여부

        Returns:
            통합된 데이터 DataFrame
        """
        start_time = time.time()

        logger.info(
            "data_fetch_started",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            parallel=parallel,
            available_sources=len(self.get_available_sources()),
        )

        if parallel:
            combined_data = self._fetch_data_parallel(symbol, start_date, end_date)
        else:
            combined_data = self._fetch_data_sequential(symbol, start_date, end_date)

        # 데이터 후처리
        if not combined_data.empty:
            combined_data = self._post_process_data(combined_data)

        elapsed_time = time.time() - start_time

        logger.info(
            "data_fetch_completed",
            symbol=symbol,
            records=len(combined_data),
            features=len(combined_data.columns) if not combined_data.empty else 0,
            elapsed_seconds=round(elapsed_time, 2),
        )

        return combined_data

    def _fetch_data_parallel(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        병렬로 데이터 수집

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            통합된 데이터 DataFrame
        """
        available_sources = self.get_available_sources()

        if not available_sources:
            logger.warning("no_available_data_sources")
            return pd.DataFrame()

        data_frames = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 각 소스에 대해 비동기 작업 제출
            future_to_source = {
                executor.submit(
                    self._fetch_from_source_with_timeout,
                    source,
                    symbol,
                    start_date,
                    end_date,
                ): source
                for source in available_sources
            }

            # 완료된 작업들 처리
            for future in as_completed(future_to_source, timeout=self.timeout_seconds):
                source = future_to_source[future]

                try:
                    data = future.result()
                    if not data.empty:
                        data_frames.append(data)

                        logger.debug(
                            "data_source_fetch_success",
                            source_name=source.name,
                            records=len(data),
                            features=len(data.columns),
                        )
                    else:
                        logger.warning(
                            "data_source_returned_empty", source_name=source.name
                        )

                except Exception as e:
                    logger.error(
                        "data_source_fetch_failed",
                        source_name=source.name,
                        error=str(e),
                    )
                    source.set_error(str(e))

        return self._combine_dataframes(data_frames)

    def _fetch_data_sequential(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        순차적으로 데이터 수집

        Args:
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            통합된 데이터 DataFrame
        """
        available_sources = self.get_available_sources()

        if not available_sources:
            logger.warning("no_available_data_sources")
            return pd.DataFrame()

        data_frames = []

        for source in available_sources:
            try:
                data = self._fetch_from_source_with_timeout(
                    source, symbol, start_date, end_date
                )

                if not data.empty:
                    data_frames.append(data)

                    logger.debug(
                        "data_source_fetch_success",
                        source_name=source.name,
                        records=len(data),
                        features=len(data.columns),
                    )
                else:
                    logger.warning(
                        "data_source_returned_empty", source_name=source.name
                    )

            except Exception as e:
                logger.error(
                    "data_source_fetch_failed", source_name=source.name, error=str(e)
                )
                source.set_error(str(e))

        return self._combine_dataframes(data_frames)

    def _fetch_from_source_with_timeout(
        self, source: DataSource, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """
        타임아웃을 적용하여 소스에서 데이터 수집

        Args:
            source: 데이터 소스
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            수집된 데이터 DataFrame
        """
        try:
            return source.fetch_data(symbol, start_date, end_date)
        except Exception as e:
            logger.error(
                "data_source_fetch_timeout_or_error",
                source_name=source.name,
                error=str(e),
            )
            source.set_error(str(e))
            return pd.DataFrame()

    def _combine_dataframes(self, data_frames: List[pd.DataFrame]) -> pd.DataFrame:
        """
        여러 DataFrame을 날짜 기준으로 통합

        Args:
            data_frames: 통합할 DataFrame 목록

        Returns:
            통합된 DataFrame
        """
        if not data_frames:
            return pd.DataFrame()

        if len(data_frames) == 1:
            return data_frames[0]

        try:
            # 날짜 인덱스 기준으로 외부 조인
            combined = data_frames[0]

            for df in data_frames[1:]:
                combined = combined.join(df, how="outer", rsuffix="_dup")

                # 중복 컬럼 처리 (원본 우선)
                dup_columns = [col for col in combined.columns if col.endswith("_dup")]
                for dup_col in dup_columns:
                    original_col = dup_col.replace("_dup", "")
                    if original_col in combined.columns:
                        # 원본 컬럼의 결측치를 중복 컬럼으로 채움
                        combined[original_col] = combined[original_col].fillna(
                            combined[dup_col]
                        )
                    combined.drop(columns=[dup_col], inplace=True)

            # 날짜순 정렬
            combined.sort_index(inplace=True)

            logger.info(
                "dataframes_combined",
                input_frames=len(data_frames),
                output_records=len(combined),
                output_features=len(combined.columns),
            )

            return combined

        except Exception as e:
            logger.error("dataframe_combination_failed", error=str(e))
            # 실패 시 첫 번째 DataFrame 반환
            return data_frames[0] if data_frames else pd.DataFrame()

    def _post_process_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        데이터 후처리 (결측치 처리, 이상치 제거 등)

        Args:
            data: 후처리할 데이터

        Returns:
            후처리된 데이터
        """
        try:
            processed_data = data.copy()

            # 1. 무한값을 NaN으로 변환
            processed_data.replace([np.inf, -np.inf], np.nan, inplace=True)

            # 2. 결측치 처리 (전진 채움 후 후진 채움)
            processed_data.fillna(method="ffill", inplace=True)
            processed_data.fillna(method="bfill", inplace=True)

            # 3. 여전히 결측치가 있는 컬럼은 0으로 채움
            processed_data.fillna(0, inplace=True)

            # 4. 데이터 타입 최적화
            for col in processed_data.select_dtypes(include=["float64"]).columns:
                processed_data[col] = processed_data[col].astype("float32")

            # 5. 이상치 제거 (IQR 방법, 수치형 컬럼만)
            numeric_columns = processed_data.select_dtypes(include=[np.number]).columns

            for col in numeric_columns:
                if col.startswith(("open", "high", "low", "close", "volume")):
                    # 가격/거래량 데이터는 이상치 제거 적용
                    Q1 = processed_data[col].quantile(0.25)
                    Q3 = processed_data[col].quantile(0.75)
                    IQR = Q3 - Q1

                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR

                    # 이상치를 경계값으로 클리핑
                    processed_data[col] = processed_data[col].clip(
                        lower_bound, upper_bound
                    )

            logger.debug(
                "data_post_processing_completed",
                input_records=len(data),
                output_records=len(processed_data),
                features=len(processed_data.columns),
            )

            return processed_data

        except Exception as e:
            logger.error("data_post_processing_failed", error=str(e))
            return data

    def validate_combined_data(
        self, data: pd.DataFrame, min_records: int = 100, max_missing_ratio: float = 0.1
    ) -> Tuple[bool, List[str]]:
        """
        통합된 데이터의 품질 검증

        Args:
            data: 검증할 데이터
            min_records: 최소 레코드 수
            max_missing_ratio: 최대 허용 결측치 비율

        Returns:
            (검증 성공 여부, 오류 메시지 목록)
        """
        errors = []

        # 1. 데이터 존재 여부
        if data.empty:
            errors.append("No data available")
            return False, errors

        # 2. 최소 레코드 수 확인
        if len(data) < min_records:
            errors.append(
                f"Insufficient data: {len(data)} records (minimum: {min_records})"
            )

        # 3. 결측치 비율 확인
        total_cells = len(data) * len(data.columns)
        missing_cells = data.isnull().sum().sum()
        missing_ratio = missing_cells / total_cells if total_cells > 0 else 0

        if missing_ratio > max_missing_ratio:
            errors.append(
                f"Too many missing values: {missing_ratio:.2%} (maximum: {max_missing_ratio:.2%})"
            )

        # 4. 필수 컬럼 확인 (가격 데이터)
        required_price_columns = ["open", "high", "low", "close"]
        missing_price_columns = [
            col for col in required_price_columns if col not in data.columns
        ]

        if missing_price_columns:
            errors.append(f"Missing required price columns: {missing_price_columns}")

        # 5. 데이터 연속성 확인 (날짜 간격)
        if len(data) > 1:
            date_gaps = pd.Series(data.index).diff().dt.days
            large_gaps = date_gaps[date_gaps > 7]  # 7일 이상 간격

            if len(large_gaps) > len(data) * 0.1:  # 10% 이상이 큰 간격
                errors.append(
                    f"Too many large date gaps: {len(large_gaps)} gaps > 7 days"
                )

        return len(errors) == 0, errors

    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 데이터 소스의 상태 정보 반환

        Returns:
            소스별 상태 정보 딕셔너리
        """
        status = {}

        for name, source in self.sources.items():
            status[name] = source.get_info()

        return status

    def reset_all_errors(self) -> None:
        """모든 데이터 소스의 오류 상태 초기화"""
        for source in self.sources.values():
            source.reset_error()

        logger.info("all_data_source_errors_reset")

    def health_check(self) -> Dict[str, Any]:
        """
        데이터 소스 매니저 상태 확인

        Returns:
            상태 정보 딕셔너리
        """
        available_sources = self.get_available_sources()
        total_sources = len(self.sources)

        return {
            "total_sources": total_sources,
            "available_sources": len(available_sources),
            "unavailable_sources": total_sources - len(available_sources),
            "source_status": self.get_source_status(),
            "total_features": len(self.get_all_feature_names()),
            "manager_config": {
                "max_workers": self.max_workers,
                "timeout_seconds": self.timeout_seconds,
            },
        }

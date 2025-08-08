"""
데이터 소스 폴백 핸들러

이 파일은 데이터 소스에서 오류가 발생했을 때의 폴백 처리 로직을 담당합니다.
우선순위 기반 폴백, 캐싱, 재시도 메커니즘 등을 제공합니다.

주요 기능:
- 우선순위 기반 폴백 처리
- 데이터 캐싱 및 복구
- 자동 재시도 메커니즘
- 부분 데이터 복구
"""

from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import date, datetime, timedelta
import pandas as pd
import time
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

from app.ml_prediction.ml.data.data_source import DataSource
from app.common.utils.logging_config import get_logger

logger = get_logger(__name__)


class FallbackStrategy(Enum):
    """폴백 전략 열거형"""

    SKIP_SOURCE = "skip_source"  # 해당 소스 건너뛰기
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # 지수 백오프로 재시도
    USE_CACHED_DATA = "use_cached_data"  # 캐시된 데이터 사용
    PARTIAL_DATA_RECOVERY = "partial_data_recovery"  # 부분 데이터 복구
    FALLBACK_TO_ALTERNATIVE = "fallback_to_alternative"  # 대체 소스 사용


@dataclass
class FallbackConfig:
    """폴백 설정"""

    max_retries: int = 3
    initial_retry_delay: float = 1.0  # 초
    max_retry_delay: float = 30.0  # 초
    backoff_multiplier: float = 2.0
    cache_ttl_hours: int = 24
    enable_partial_recovery: bool = True
    min_data_completeness: float = 0.7  # 70% 이상 데이터가 있어야 함


@dataclass
class DataCacheEntry:
    """데이터 캐시 엔트리"""

    data: pd.DataFrame
    timestamp: datetime
    source_name: str
    symbol: str
    start_date: date
    end_date: date
    checksum: str


class DataSourceFallbackHandler:
    """
    데이터 소스 폴백 핸들러

    데이터 소스에서 오류가 발생했을 때 다양한 폴백 전략을 적용합니다.
    """

    def __init__(self, config: Optional[FallbackConfig] = None):
        """
        폴백 핸들러 초기화

        Args:
            config: 폴백 설정
        """
        self.config = config or FallbackConfig()
        self.data_cache: Dict[str, DataCacheEntry] = {}
        self.source_failure_counts: Dict[str, int] = {}
        self.source_last_success: Dict[str, datetime] = {}

    def handle_source_failure(
        self,
        source: DataSource,
        symbol: str,
        start_date: date,
        end_date: date,
        error: Exception,
        alternative_sources: List[DataSource] = None,
    ) -> Tuple[Optional[pd.DataFrame], FallbackStrategy]:
        """
        데이터 소스 실패 처리

        Args:
            source: 실패한 데이터 소스
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
            error: 발생한 오류
            alternative_sources: 대체 가능한 데이터 소스들

        Returns:
            (복구된 데이터, 사용된 폴백 전략)
        """
        logger.warning(
            "data_source_failure_detected",
            source_name=source.name,
            symbol=symbol,
            error=str(error),
        )

        # 실패 횟수 증가
        self.source_failure_counts[source.name] = (
            self.source_failure_counts.get(source.name, 0) + 1
        )

        # 폴백 전략 결정
        strategy = self._determine_fallback_strategy(source, error)

        logger.info(
            "fallback_strategy_selected",
            source_name=source.name,
            strategy=strategy.value,
            failure_count=self.source_failure_counts[source.name],
        )

        # 전략에 따른 처리
        if strategy == FallbackStrategy.RETRY_WITH_BACKOFF:
            return self._retry_with_backoff(source, symbol, start_date, end_date)

        elif strategy == FallbackStrategy.USE_CACHED_DATA:
            return self._use_cached_data(source, symbol, start_date, end_date)

        elif strategy == FallbackStrategy.PARTIAL_DATA_RECOVERY:
            return self._partial_data_recovery(source, symbol, start_date, end_date)

        elif strategy == FallbackStrategy.FALLBACK_TO_ALTERNATIVE:
            return self._fallback_to_alternative(
                alternative_sources or [], symbol, start_date, end_date
            )

        else:  # SKIP_SOURCE
            return None, strategy

    def _determine_fallback_strategy(
        self, source: DataSource, error: Exception
    ) -> FallbackStrategy:
        """
        오류 유형과 소스 상태에 따른 폴백 전략 결정

        Args:
            source: 실패한 데이터 소스
            error: 발생한 오류

        Returns:
            선택된 폴백 전략
        """
        failure_count = self.source_failure_counts.get(source.name, 0)

        # 네트워크 관련 오류는 재시도
        if any(
            keyword in str(error).lower()
            for keyword in ["timeout", "connection", "network", "unreachable"]
        ):
            if failure_count < self.config.max_retries:
                return FallbackStrategy.RETRY_WITH_BACKOFF

        # 데이터베이스 관련 오류는 캐시 사용 시도
        if any(
            keyword in str(error).lower()
            for keyword in ["database", "sql", "connection pool", "deadlock"]
        ):
            return FallbackStrategy.USE_CACHED_DATA

        # 부분 데이터 오류는 부분 복구 시도
        if any(
            keyword in str(error).lower()
            for keyword in ["incomplete", "partial", "missing data"]
        ):
            if self.config.enable_partial_recovery:
                return FallbackStrategy.PARTIAL_DATA_RECOVERY

        # 권한 오류나 설정 오류는 대체 소스 사용
        if any(
            keyword in str(error).lower()
            for keyword in ["permission", "unauthorized", "forbidden", "access denied"]
        ):
            return FallbackStrategy.FALLBACK_TO_ALTERNATIVE

        # 기본적으로 재시도 후 건너뛰기
        if failure_count < self.config.max_retries:
            return FallbackStrategy.RETRY_WITH_BACKOFF
        else:
            return FallbackStrategy.SKIP_SOURCE

    def _retry_with_backoff(
        self, source: DataSource, symbol: str, start_date: date, end_date: date
    ) -> Tuple[Optional[pd.DataFrame], FallbackStrategy]:
        """
        지수 백오프를 사용한 재시도

        Args:
            source: 재시도할 데이터 소스
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            (복구된 데이터, 폴백 전략)
        """
        failure_count = self.source_failure_counts.get(source.name, 0)

        for attempt in range(1, self.config.max_retries + 1):
            # 지수 백오프 계산
            delay = min(
                self.config.initial_retry_delay
                * (self.config.backoff_multiplier ** (attempt - 1)),
                self.config.max_retry_delay,
            )

            logger.info(
                "retrying_data_source",
                source_name=source.name,
                attempt=attempt,
                delay_seconds=delay,
            )

            time.sleep(delay)

            try:
                # 소스 오류 상태 초기화
                source.reset_error()

                # 재시도
                data = source.fetch_data(symbol, start_date, end_date)

                if not data.empty:
                    # 성공 시 실패 카운트 초기화
                    self.source_failure_counts[source.name] = 0
                    self.source_last_success[source.name] = datetime.now()

                    # 캐시에 저장
                    self._cache_data(data, source.name, symbol, start_date, end_date)

                    logger.info(
                        "data_source_retry_success",
                        source_name=source.name,
                        attempt=attempt,
                        records=len(data),
                    )

                    return data, FallbackStrategy.RETRY_WITH_BACKOFF

            except Exception as retry_error:
                logger.warning(
                    "data_source_retry_failed",
                    source_name=source.name,
                    attempt=attempt,
                    error=str(retry_error),
                )

                if attempt == self.config.max_retries:
                    source.set_error(f"Max retries exceeded: {str(retry_error)}")

        return None, FallbackStrategy.RETRY_WITH_BACKOFF

    def _use_cached_data(
        self, source: DataSource, symbol: str, start_date: date, end_date: date
    ) -> Tuple[Optional[pd.DataFrame], FallbackStrategy]:
        """
        캐시된 데이터 사용

        Args:
            source: 데이터 소스
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            (캐시된 데이터, 폴백 전략)
        """
        cache_key = self._generate_cache_key(source.name, symbol, start_date, end_date)

        if cache_key in self.data_cache:
            cache_entry = self.data_cache[cache_key]

            # 캐시 유효성 확인
            if self._is_cache_valid(cache_entry):
                logger.info(
                    "using_cached_data",
                    source_name=source.name,
                    symbol=symbol,
                    cache_age_hours=self._get_cache_age_hours(cache_entry),
                    records=len(cache_entry.data),
                )

                return cache_entry.data.copy(), FallbackStrategy.USE_CACHED_DATA
            else:
                # 만료된 캐시 제거
                del self.data_cache[cache_key]

                logger.warning(
                    "cached_data_expired", source_name=source.name, symbol=symbol
                )

        logger.warning("no_valid_cached_data", source_name=source.name, symbol=symbol)

        return None, FallbackStrategy.USE_CACHED_DATA

    def _partial_data_recovery(
        self, source: DataSource, symbol: str, start_date: date, end_date: date
    ) -> Tuple[Optional[pd.DataFrame], FallbackStrategy]:
        """
        부분 데이터 복구 시도

        Args:
            source: 데이터 소스
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            (부분 복구된 데이터, 폴백 전략)
        """
        logger.info(
            "attempting_partial_data_recovery",
            source_name=source.name,
            symbol=symbol,
            date_range_days=(end_date - start_date).days,
        )

        # 날짜 범위를 작은 청크로 나누어 시도
        chunk_size_days = 30  # 30일씩 청크
        current_date = start_date
        partial_data_frames = []

        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_size_days), end_date)

            try:
                source.reset_error()
                chunk_data = source.fetch_data(symbol, current_date, chunk_end)

                if not chunk_data.empty:
                    partial_data_frames.append(chunk_data)

                    logger.debug(
                        "partial_data_chunk_recovered",
                        source_name=source.name,
                        chunk_start=current_date,
                        chunk_end=chunk_end,
                        records=len(chunk_data),
                    )

            except Exception as chunk_error:
                logger.warning(
                    "partial_data_chunk_failed",
                    source_name=source.name,
                    chunk_start=current_date,
                    chunk_end=chunk_end,
                    error=str(chunk_error),
                )

            current_date = chunk_end + timedelta(days=1)

        # 부분 데이터 통합
        if partial_data_frames:
            combined_data = pd.concat(partial_data_frames, ignore_index=False)
            combined_data.sort_index(inplace=True)

            # 데이터 완성도 확인
            expected_days = (end_date - start_date).days + 1
            actual_days = len(combined_data)
            completeness = actual_days / expected_days

            if completeness >= self.config.min_data_completeness:
                logger.info(
                    "partial_data_recovery_success",
                    source_name=source.name,
                    symbol=symbol,
                    completeness=f"{completeness:.2%}",
                    records=len(combined_data),
                )

                # 부분 데이터도 캐시에 저장
                self._cache_data(
                    combined_data, source.name, symbol, start_date, end_date
                )

                return combined_data, FallbackStrategy.PARTIAL_DATA_RECOVERY
            else:
                logger.warning(
                    "partial_data_recovery_insufficient",
                    source_name=source.name,
                    symbol=symbol,
                    completeness=f"{completeness:.2%}",
                    min_required=f"{self.config.min_data_completeness:.2%}",
                )

        return None, FallbackStrategy.PARTIAL_DATA_RECOVERY

    def _fallback_to_alternative(
        self,
        alternative_sources: List[DataSource],
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> Tuple[Optional[pd.DataFrame], FallbackStrategy]:
        """
        대체 데이터 소스 사용

        Args:
            alternative_sources: 대체 가능한 데이터 소스들
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            (대체 소스 데이터, 폴백 전략)
        """
        if not alternative_sources:
            logger.warning("no_alternative_sources_available")
            return None, FallbackStrategy.FALLBACK_TO_ALTERNATIVE

        # 우선순위 순으로 정렬
        sorted_alternatives = sorted(alternative_sources, key=lambda x: x.priority)

        for alt_source in sorted_alternatives:
            if not alt_source.is_available():
                continue

            try:
                logger.info(
                    "trying_alternative_source",
                    alternative_source=alt_source.name,
                    symbol=symbol,
                )

                data = alt_source.fetch_data(symbol, start_date, end_date)

                if not data.empty:
                    logger.info(
                        "alternative_source_success",
                        alternative_source=alt_source.name,
                        symbol=symbol,
                        records=len(data),
                    )

                    # 대체 소스 데이터도 캐시에 저장
                    self._cache_data(
                        data, alt_source.name, symbol, start_date, end_date
                    )

                    return data, FallbackStrategy.FALLBACK_TO_ALTERNATIVE

            except Exception as alt_error:
                logger.warning(
                    "alternative_source_failed",
                    alternative_source=alt_source.name,
                    error=str(alt_error),
                )
                alt_source.set_error(str(alt_error))

        logger.error("all_alternative_sources_failed")
        return None, FallbackStrategy.FALLBACK_TO_ALTERNATIVE

    def _cache_data(
        self,
        data: pd.DataFrame,
        source_name: str,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> None:
        """
        데이터를 캐시에 저장

        Args:
            data: 저장할 데이터
            source_name: 데이터 소스 이름
            symbol: 심볼
            start_date: 시작 날짜
            end_date: 종료 날짜
        """
        try:
            cache_key = self._generate_cache_key(
                source_name, symbol, start_date, end_date
            )
            checksum = self._calculate_data_checksum(data)

            cache_entry = DataCacheEntry(
                data=data.copy(),
                timestamp=datetime.now(),
                source_name=source_name,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                checksum=checksum,
            )

            self.data_cache[cache_key] = cache_entry

            logger.debug(
                "data_cached",
                source_name=source_name,
                symbol=symbol,
                cache_key=cache_key,
                records=len(data),
            )

        except Exception as e:
            logger.error(
                "data_caching_failed",
                source_name=source_name,
                symbol=symbol,
                error=str(e),
            )

    def _generate_cache_key(
        self, source_name: str, symbol: str, start_date: date, end_date: date
    ) -> str:
        """캐시 키 생성"""
        key_data = f"{source_name}:{symbol}:{start_date}:{end_date}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _calculate_data_checksum(self, data: pd.DataFrame) -> str:
        """데이터 체크섬 계산"""
        try:
            data_str = data.to_string()
            return hashlib.md5(data_str.encode()).hexdigest()
        except Exception:
            return ""

    def _is_cache_valid(self, cache_entry: DataCacheEntry) -> bool:
        """캐시 유효성 확인"""
        age_hours = self._get_cache_age_hours(cache_entry)
        return age_hours <= self.config.cache_ttl_hours

    def _get_cache_age_hours(self, cache_entry: DataCacheEntry) -> float:
        """캐시 나이 계산 (시간 단위)"""
        age_delta = datetime.now() - cache_entry.timestamp
        return age_delta.total_seconds() / 3600

    def clear_cache(self, source_name: Optional[str] = None) -> int:
        """
        캐시 정리

        Args:
            source_name: 특정 소스의 캐시만 정리 (None이면 전체)

        Returns:
            정리된 캐시 엔트리 수
        """
        if source_name:
            # 특정 소스의 캐시만 정리
            keys_to_remove = [
                key
                for key, entry in self.data_cache.items()
                if entry.source_name == source_name
            ]
        else:
            # 전체 캐시 정리
            keys_to_remove = list(self.data_cache.keys())

        for key in keys_to_remove:
            del self.data_cache[key]

        logger.info(
            "cache_cleared",
            source_name=source_name or "all",
            cleared_entries=len(keys_to_remove),
        )

        return len(keys_to_remove)

    def clear_expired_cache(self) -> int:
        """
        만료된 캐시 엔트리 정리

        Returns:
            정리된 캐시 엔트리 수
        """
        expired_keys = [
            key
            for key, entry in self.data_cache.items()
            if not self._is_cache_valid(entry)
        ]

        for key in expired_keys:
            del self.data_cache[key]

        logger.info("expired_cache_cleared", cleared_entries=len(expired_keys))

        return len(expired_keys)

    def get_fallback_statistics(self) -> Dict[str, Any]:
        """
        폴백 통계 정보 반환

        Returns:
            폴백 통계 딕셔너리
        """
        return {
            "source_failure_counts": self.source_failure_counts.copy(),
            "source_last_success": {
                name: timestamp.isoformat()
                for name, timestamp in self.source_last_success.items()
            },
            "cache_entries": len(self.data_cache),
            "cache_size_mb": self._calculate_cache_size_mb(),
            "config": {
                "max_retries": self.config.max_retries,
                "cache_ttl_hours": self.config.cache_ttl_hours,
                "min_data_completeness": self.config.min_data_completeness,
            },
        }

    def _calculate_cache_size_mb(self) -> float:
        """캐시 크기 계산 (MB 단위)"""
        try:
            total_size = 0
            for entry in self.data_cache.values():
                # DataFrame 메모리 사용량 추정
                total_size += entry.data.memory_usage(deep=True).sum()

            return total_size / (1024 * 1024)  # MB 변환
        except Exception:
            return 0.0

    def reset_failure_counts(self, source_name: Optional[str] = None) -> None:
        """
        실패 카운트 초기화

        Args:
            source_name: 특정 소스만 초기화 (None이면 전체)
        """
        if source_name:
            if source_name in self.source_failure_counts:
                self.source_failure_counts[source_name] = 0
                logger.info("failure_count_reset", source_name=source_name)
        else:
            self.source_failure_counts.clear()
            logger.info("all_failure_counts_reset")

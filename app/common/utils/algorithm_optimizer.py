"""
알고리즘 최적화 유틸리티

기술적 지표 계산, 데이터 처리 등의 핵심 알고리즘을 최적화하여
성능을 크게 향상시키는 유틸리티들을 제공합니다.
"""

import numpy as np
import pandas as pd
import numba
from numba import jit, prange
from typing import Union, Tuple, Optional, List, Dict, Any
import time
from functools import wraps, lru_cache
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing as mp

from app.common.utils.logging_config import get_logger
from app.common.utils.memory_optimizer import memory_monitor

logger = get_logger(__name__)


# =============================================================================
# 성능 측정 데코레이터
# =============================================================================


def benchmark(func):
    """성능 벤치마킹 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        execution_time = end_time - start_time
        logger.info(
            "algorithm_benchmark",
            function=func.__name__,
            execution_time_ms=round(execution_time * 1000, 3),
            args_count=len(args),
            kwargs_count=len(kwargs),
        )

        return result

    return wrapper


def profile_memory_usage(func):
    """메모리 사용량 프로파일링 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        result = func(*args, **kwargs)

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_diff = memory_after - memory_before

        logger.info(
            "memory_profile",
            function=func.__name__,
            memory_before_mb=round(memory_before, 2),
            memory_after_mb=round(memory_after, 2),
            memory_diff_mb=round(memory_diff, 2),
        )

        return result

    return wrapper


# =============================================================================
# 고성능 기술적 지표 계산 (Numba JIT 최적화)
# =============================================================================


@jit(nopython=True, cache=True)
def fast_sma(prices: np.ndarray, period: int) -> np.ndarray:
    """
    고성능 단순이동평균 계산 (Numba JIT 최적화)

    Args:
        prices: 가격 배열
        period: 이동평균 기간

    Returns:
        이동평균 배열
    """
    n = len(prices)
    sma = np.full(n, np.nan)

    if n < period:
        return sma

    # 첫 번째 SMA 계산
    sma[period - 1] = np.mean(prices[:period])

    # 나머지 SMA 계산 (슬라이딩 윈도우)
    for i in range(period, n):
        sma[i] = sma[i - 1] + (prices[i] - prices[i - period]) / period

    return sma


@jit(nopython=True, cache=True)
def fast_ema(prices: np.ndarray, period: int) -> np.ndarray:
    """
    고성능 지수이동평균 계산 (Numba JIT 최적화)

    Args:
        prices: 가격 배열
        period: EMA 기간

    Returns:
        EMA 배열
    """
    n = len(prices)
    ema = np.full(n, np.nan)

    if n == 0:
        return ema

    alpha = 2.0 / (period + 1)

    # 첫 번째 값은 가격 그대로
    ema[0] = prices[0]

    # 나머지 EMA 계산
    for i in range(1, n):
        ema[i] = alpha * prices[i] + (1 - alpha) * ema[i - 1]

    return ema


@jit(nopython=True, cache=True)
def fast_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """
    고성능 RSI 계산 (Numba JIT 최적화)

    Args:
        prices: 가격 배열
        period: RSI 기간

    Returns:
        RSI 배열
    """
    n = len(prices)
    rsi = np.full(n, np.nan)

    if n < period + 1:
        return rsi

    # 가격 변화 계산
    deltas = np.diff(prices)

    # 상승분과 하락분 분리
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # 첫 번째 평균 계산
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100.0 - (100.0 / (1.0 + rs))

    # 나머지 RSI 계산 (Wilder's smoothing)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period

        if avg_loss == 0:
            rsi[i] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi


@jit(nopython=True, cache=True)
def fast_bollinger_bands(
    prices: np.ndarray, period: int = 20, std_dev: float = 2.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    고성능 볼린저 밴드 계산 (Numba JIT 최적화)

    Args:
        prices: 가격 배열
        period: 이동평균 기간
        std_dev: 표준편차 배수

    Returns:
        (상단밴드, 중간선, 하단밴드) 튜플
    """
    n = len(prices)
    middle = np.full(n, np.nan)
    upper = np.full(n, np.nan)
    lower = np.full(n, np.nan)

    if n < period:
        return upper, middle, lower

    # 이동평균과 표준편차 계산
    for i in range(period - 1, n):
        window = prices[i - period + 1 : i + 1]
        mean_val = np.mean(window)
        std_val = np.std(window)

        middle[i] = mean_val
        upper[i] = mean_val + std_dev * std_val
        lower[i] = mean_val - std_dev * std_val

    return upper, middle, lower


@jit(nopython=True, cache=True)
def fast_macd(
    prices: np.ndarray,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    고성능 MACD 계산 (Numba JIT 최적화)

    Args:
        prices: 가격 배열
        fast_period: 빠른 EMA 기간
        slow_period: 느린 EMA 기간
        signal_period: 시그널 라인 기간

    Returns:
        (MACD, Signal, Histogram) 튜플
    """
    # 빠른 EMA와 느린 EMA 계산
    fast_ema = fast_ema(prices, fast_period)
    slow_ema = fast_ema(prices, slow_period)

    # MACD 라인 계산
    macd_line = fast_ema - slow_ema

    # 시그널 라인 계산 (MACD의 EMA)
    signal_line = fast_ema(macd_line[~np.isnan(macd_line)], signal_period)

    # 전체 길이에 맞게 시그널 라인 조정
    n = len(prices)
    full_signal = np.full(n, np.nan)
    valid_start = slow_period - 1
    signal_start = valid_start + signal_period - 1

    if signal_start < n:
        full_signal[signal_start : signal_start + len(signal_line)] = signal_line

    # 히스토그램 계산
    histogram = macd_line - full_signal

    return macd_line, full_signal, histogram


# =============================================================================
# 병렬 처리 최적화
# =============================================================================


class ParallelTechnicalAnalyzer:
    """병렬 처리 기술적 분석기"""

    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or mp.cpu_count()
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=self.max_workers)

    @benchmark
    @memory_monitor(threshold_mb=200.0)
    def calculate_multiple_indicators_parallel(
        self, price_data: Dict[str, np.ndarray], indicators: List[str] = None
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """
        여러 심볼의 기술적 지표를 병렬로 계산

        Args:
            price_data: 심볼별 가격 데이터 딕셔너리
            indicators: 계산할 지표 리스트

        Returns:
            심볼별 지표 결과 딕셔너리
        """
        if indicators is None:
            indicators = ["sma_20", "ema_12", "rsi", "bollinger", "macd"]

        logger.info(
            "parallel_indicator_calculation_started",
            symbol_count=len(price_data),
            indicator_count=len(indicators),
        )

        # 작업 분할
        tasks = []
        for symbol, prices in price_data.items():
            tasks.append((symbol, prices, indicators))

        # 병렬 실행
        with self.process_executor as executor:
            results = list(executor.map(self._calculate_indicators_for_symbol, tasks))

        # 결과 정리
        final_results = {}
        for symbol, indicator_results in results:
            final_results[symbol] = indicator_results

        logger.info(
            "parallel_indicator_calculation_completed", symbol_count=len(final_results)
        )

        return final_results

    @staticmethod
    def _calculate_indicators_for_symbol(
        task_data: Tuple[str, np.ndarray, List[str]]
    ) -> Tuple[str, Dict[str, np.ndarray]]:
        """단일 심볼의 지표 계산 (정적 메서드로 pickle 가능)"""
        symbol, prices, indicators = task_data
        results = {}

        for indicator in indicators:
            if indicator == "sma_20":
                results["sma_20"] = fast_sma(prices, 20)
            elif indicator == "sma_50":
                results["sma_50"] = fast_sma(prices, 50)
            elif indicator == "ema_12":
                results["ema_12"] = fast_ema(prices, 12)
            elif indicator == "ema_26":
                results["ema_26"] = fast_ema(prices, 26)
            elif indicator == "rsi":
                results["rsi"] = fast_rsi(prices, 14)
            elif indicator == "bollinger":
                upper, middle, lower = fast_bollinger_bands(prices, 20, 2.0)
                results["bb_upper"] = upper
                results["bb_middle"] = middle
                results["bb_lower"] = lower
            elif indicator == "macd":
                macd, signal, histogram = fast_macd(prices, 12, 26, 9)
                results["macd"] = macd
                results["macd_signal"] = signal
                results["macd_histogram"] = histogram

        return symbol, results

    def __del__(self):
        """리소스 정리"""
        if hasattr(self, "thread_executor"):
            self.thread_executor.shutdown(wait=True)
        if hasattr(self, "process_executor"):
            self.process_executor.shutdown(wait=True)


# =============================================================================
# 스마트 캐싱 시스템
# =============================================================================


class SmartCache:
    """스마트 캐싱 시스템"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache = {}
        self.access_count = {}
        self.computation_time = {}

    def _generate_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """캐시 키 생성"""
        import hashlib

        # 인자들을 문자열로 변환
        args_str = str(args) + str(sorted(kwargs.items()))

        # 해시 생성
        hash_obj = hashlib.md5(args_str.encode())
        return f"{func_name}:{hash_obj.hexdigest()}"

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회"""
        if key in self.cache:
            self.access_count[key] = self.access_count.get(key, 0) + 1
            return self.cache[key]
        return None

    def set(self, key: str, value: Any, computation_time: float = 0):
        """캐시에 값 저장"""
        # 캐시 크기 제한
        if len(self.cache) >= self.max_size:
            self._evict_least_valuable()

        self.cache[key] = value
        self.access_count[key] = 1
        self.computation_time[key] = computation_time

    def _evict_least_valuable(self):
        """가장 가치가 낮은 항목 제거"""
        if not self.cache:
            return

        # 가치 점수 계산 (접근 횟수 * 계산 시간)
        scores = {}
        for key in self.cache:
            access = self.access_count.get(key, 1)
            comp_time = self.computation_time.get(key, 1)
            scores[key] = access * comp_time

        # 가장 낮은 점수의 항목 제거
        least_valuable = min(scores, key=scores.get)

        del self.cache[least_valuable]
        del self.access_count[least_valuable]
        del self.computation_time[least_valuable]

    def clear(self):
        """캐시 전체 삭제"""
        self.cache.clear()
        self.access_count.clear()
        self.computation_time.clear()

    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "total_access_count": sum(self.access_count.values()),
            "avg_computation_time": (
                sum(self.computation_time.values()) / len(self.computation_time)
                if self.computation_time
                else 0
            ),
        }


# 전역 스마트 캐시
smart_cache = SmartCache(max_size=2000)


def smart_cached(func):
    """스마트 캐싱 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 캐시 키 생성
        cache_key = smart_cache._generate_cache_key(func.__name__, *args, **kwargs)

        # 캐시에서 조회
        cached_result = smart_cache.get(cache_key)
        if cached_result is not None:
            logger.debug("smart_cache_hit", function=func.__name__)
            return cached_result

        # 함수 실행 및 시간 측정
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        computation_time = time.perf_counter() - start_time

        # 캐시에 저장
        smart_cache.set(cache_key, result, computation_time)

        logger.debug(
            "smart_cache_miss",
            function=func.__name__,
            computation_time_ms=round(computation_time * 1000, 3),
        )

        return result

    return wrapper


# =============================================================================
# 최적화된 기술적 분석 클래스
# =============================================================================


class OptimizedTechnicalAnalyzer:
    """최적화된 기술적 분석기"""

    def __init__(self):
        self.parallel_analyzer = ParallelTechnicalAnalyzer()

    @smart_cached
    @benchmark
    def calculate_sma(
        self, prices: Union[pd.Series, np.ndarray], period: int
    ) -> np.ndarray:
        """최적화된 SMA 계산"""
        if isinstance(prices, pd.Series):
            prices = prices.values

        return fast_sma(prices, period)

    @smart_cached
    @benchmark
    def calculate_ema(
        self, prices: Union[pd.Series, np.ndarray], period: int
    ) -> np.ndarray:
        """최적화된 EMA 계산"""
        if isinstance(prices, pd.Series):
            prices = prices.values

        return fast_ema(prices, period)

    @smart_cached
    @benchmark
    def calculate_rsi(
        self, prices: Union[pd.Series, np.ndarray], period: int = 14
    ) -> np.ndarray:
        """최적화된 RSI 계산"""
        if isinstance(prices, pd.Series):
            prices = prices.values

        return fast_rsi(prices, period)

    @smart_cached
    @benchmark
    def calculate_bollinger_bands(
        self,
        prices: Union[pd.Series, np.ndarray],
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Dict[str, np.ndarray]:
        """최적화된 볼린저 밴드 계산"""
        if isinstance(prices, pd.Series):
            prices = prices.values

        upper, middle, lower = fast_bollinger_bands(prices, period, std_dev)

        return {"upper": upper, "middle": middle, "lower": lower}

    @smart_cached
    @benchmark
    def calculate_macd(
        self,
        prices: Union[pd.Series, np.ndarray],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ) -> Dict[str, np.ndarray]:
        """최적화된 MACD 계산"""
        if isinstance(prices, pd.Series):
            prices = prices.values

        macd, signal, histogram = fast_macd(
            prices, fast_period, slow_period, signal_period
        )

        return {"macd": macd, "signal": signal, "histogram": histogram}

    @benchmark
    def calculate_all_indicators(
        self, prices: Union[pd.Series, np.ndarray]
    ) -> Dict[str, Union[np.ndarray, Dict[str, np.ndarray]]]:
        """모든 주요 지표를 한 번에 계산"""
        if isinstance(prices, pd.Series):
            prices = prices.values

        results = {}

        # 이동평균들
        results["sma_20"] = self.calculate_sma(prices, 20)
        results["sma_50"] = self.calculate_sma(prices, 50)
        results["ema_12"] = self.calculate_ema(prices, 12)
        results["ema_26"] = self.calculate_ema(prices, 26)

        # 모멘텀 지표들
        results["rsi"] = self.calculate_rsi(prices, 14)

        # 변동성 지표들
        results["bollinger"] = self.calculate_bollinger_bands(prices, 20, 2.0)

        # 추세 지표들
        results["macd"] = self.calculate_macd(prices, 12, 26, 9)

        return results

    def batch_calculate_indicators(
        self, price_data: Dict[str, Union[pd.Series, np.ndarray]]
    ) -> Dict[str, Dict[str, Union[np.ndarray, Dict[str, np.ndarray]]]]:
        """여러 심볼의 지표를 배치로 계산"""
        # numpy 배열로 변환
        np_price_data = {}
        for symbol, prices in price_data.items():
            if isinstance(prices, pd.Series):
                np_price_data[symbol] = prices.values
            else:
                np_price_data[symbol] = prices

        # 병렬 계산
        return self.parallel_analyzer.calculate_multiple_indicators_parallel(
            np_price_data
        )


# 전역 최적화된 분석기
optimized_analyzer = OptimizedTechnicalAnalyzer()


# =============================================================================
# 성능 벤치마킹 도구
# =============================================================================


class PerformanceBenchmark:
    """성능 벤치마킹 도구"""

    def __init__(self):
        self.results = []

    def benchmark_function(
        self, func: callable, args: tuple, kwargs: dict = None, iterations: int = 100
    ) -> Dict[str, Any]:
        """함수 성능 벤치마킹"""
        if kwargs is None:
            kwargs = {}

        times = []

        # 워밍업
        for _ in range(5):
            func(*args, **kwargs)

        # 실제 측정
        for _ in range(iterations):
            start_time = time.perf_counter()
            result = func(*args, **kwargs)
            end_time = time.perf_counter()
            times.append(end_time - start_time)

        # 통계 계산
        times = np.array(times)
        benchmark_result = {
            "function_name": func.__name__,
            "iterations": iterations,
            "mean_time_ms": round(np.mean(times) * 1000, 3),
            "median_time_ms": round(np.median(times) * 1000, 3),
            "std_time_ms": round(np.std(times) * 1000, 3),
            "min_time_ms": round(np.min(times) * 1000, 3),
            "max_time_ms": round(np.max(times) * 1000, 3),
            "total_time_ms": round(np.sum(times) * 1000, 3),
        }

        self.results.append(benchmark_result)

        logger.info("function_benchmarked", **benchmark_result)

        return benchmark_result

    def compare_implementations(
        self,
        implementations: Dict[str, callable],
        args: tuple,
        kwargs: dict = None,
        iterations: int = 100,
    ) -> Dict[str, Any]:
        """여러 구현체 성능 비교"""
        if kwargs is None:
            kwargs = {}

        comparison_results = {}

        for name, func in implementations.items():
            result = self.benchmark_function(func, args, kwargs, iterations)
            comparison_results[name] = result

        # 가장 빠른 구현체 찾기
        fastest = min(comparison_results.values(), key=lambda x: x["mean_time_ms"])

        # 상대적 성능 계산
        for name, result in comparison_results.items():
            speedup = fastest["mean_time_ms"] / result["mean_time_ms"]
            result["speedup_factor"] = round(speedup, 2)
            result["is_fastest"] = result == fastest

        logger.info(
            "implementation_comparison_completed",
            implementations_count=len(implementations),
            fastest_implementation=fastest["function_name"],
        )

        return comparison_results

    def get_summary(self) -> Dict[str, Any]:
        """벤치마킹 결과 요약"""
        if not self.results:
            return {"message": "벤치마킹 결과가 없습니다"}

        return {
            "total_benchmarks": len(self.results),
            "results": self.results,
            "fastest_function": min(self.results, key=lambda x: x["mean_time_ms"])[
                "function_name"
            ],
            "slowest_function": max(self.results, key=lambda x: x["mean_time_ms"])[
                "function_name"
            ],
        }


# 전역 벤치마킹 도구
performance_benchmark = PerformanceBenchmark()

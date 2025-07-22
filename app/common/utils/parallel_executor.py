"""
병렬 작업 실행을 위한 유틸리티
"""

import time
import concurrent.futures
from typing import List, Callable, Any, Optional
from functools import wraps


class ParallelExecutor:
    """병렬 작업 실행을 위한 클래스"""

    def __init__(self, max_workers: int = 5):  # 10 → 5로 감소 (DB 연결 부하 감소)
        self.max_workers = max_workers

    def run_parallel(self, tasks: List[tuple], timeout: int = 300) -> List[Any]:
        """
        여러 작업을 병렬로 실행

        Args:
            tasks: [(함수, 인자들), ...] 형태의 작업 리스트
            timeout: 전체 작업 타임아웃 (초)

        Returns:
            각 작업의 결과 리스트
        """
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers
        ) as executor:
            futures = []

            for func, args in tasks:
                if isinstance(args, tuple):
                    future = executor.submit(func, *args)
                else:
                    future = executor.submit(func, args)
                futures.append(future)

            results = []
            for future in concurrent.futures.as_completed(futures, timeout=timeout):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"작업 실행 중 오류: {e}")
                    results.append(None)

            return results

    def run_symbol_tasks_parallel(
        self, func: Callable, symbols: List[str], delay: float = 0
    ) -> List[Any]:
        """
        심볼별 작업을 병렬로 실행 (API 제한 고려)

        Args:
            func: 실행할 함수
            symbols: 심볼 리스트
            delay: 각 작업 간 지연 시간 (초)

        Returns:
            각 심볼별 작업 결과
        """
        # 배치 크기 제한 (DB 연결 부하 감소)
        batch_size = max(1, min(3, self.max_workers // 2))  # 최대 3개로 제한
        results = []

        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i : i + batch_size]
            tasks = [(func, symbol) for symbol in batch_symbols]
            batch_results = self.run_parallel(tasks)
            results.extend(batch_results)

            # 배치 간 지연 추가 (DB 연결 풀 회복 시간)
            if i + batch_size < len(symbols):
                sleep_time = delay if delay > 0 else 1.0  # 최소 1초 지연
                time.sleep(sleep_time)

        return results


def retry_on_failure(
    max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0
):
    """재시도 데코레이터 (exponential backoff)"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e

                    wait_time = delay * (backoff_factor**attempt)
                    print(
                        f"재시도 {attempt + 1}/{max_retries}: {e} (대기: {wait_time:.1f}초)"
                    )
                    time.sleep(wait_time)
            return None

        return wrapper

    return decorator


def measure_execution_time(func):
    """실행 시간 측정 데코레이터"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"⏱️ {func.__name__} 실행 시간: {execution_time:.2f}초")
        return result

    return wrapper

"""
비동기 작업 실행을 위한 유틸리티

이 모듈은 FastAPI의 비동기 기능을 활용하여 외부 API 호출 등의 I/O 작업을
효율적으로 처리하기 위한 유틸리티를 제공합니다.
"""

import asyncio
import time
from typing import List, Dict, Any, Callable, Coroutine, TypeVar, Optional
from functools import wraps

T = TypeVar("T")


class AsyncExecutor:
    """비동기 작업 실행을 위한 클래스"""

    def __init__(self, max_concurrency: int = 10):
        """
        Args:
            max_concurrency: 동시 실행할 최대 작업 수 (세마포어 제한)
        """
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def run_with_semaphore(self, coro):
        """세마포어로 동시성 제한하여 코루틴 실행"""
        async with self.semaphore:
            return await coro

    async def gather_with_concurrency(self, tasks: List[Coroutine]) -> List[Any]:
        """
        동시성 제한을 적용하여 여러 비동기 작업 실행

        Args:
            tasks: 실행할 코루틴 목록

        Returns:
            각 작업의 결과 리스트
        """
        # 세마포어로 래핑
        limited_tasks = [self.run_with_semaphore(task) for task in tasks]

        # 모든 작업 실행 및 결과 수집
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)

        # 예외 처리
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                print(f"작업 실행 중 오류: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results

    async def run_tasks_with_delay(
        self, tasks: List[Coroutine], delay: float = 0.1
    ) -> List[Any]:
        """
        작업 간 지연을 두고 순차적으로 실행 (API 제한 대응)

        Args:
            tasks: 실행할 코루틴 목록
            delay: 각 작업 간 지연 시간 (초)

        Returns:
            각 작업의 결과 리스트
        """
        results = []

        for task in tasks:
            try:
                result = await task
                results.append(result)
            except Exception as e:
                print(f"작업 실행 중 오류: {e}")
                results.append(None)

            # 다음 작업 전 지연
            if delay > 0:
                await asyncio.sleep(delay)

        return results

    async def process_batch(
        self,
        items: List[Any],
        processor: Callable[[Any], Coroutine],
        batch_size: int = 5,
        batch_delay: float = 1.0,
    ) -> List[Any]:
        """
        항목들을 배치로 나누어 처리 (API 제한 대응)

        Args:
            items: 처리할 항목 리스트
            processor: 각 항목을 처리할 비동기 함수
            batch_size: 배치 크기
            batch_delay: 배치 간 지연 시간 (초)

        Returns:
            처리 결과 리스트
        """
        all_results = []

        # 배치 단위로 처리
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]

            # 현재 배치의 작업 생성
            batch_tasks = [processor(item) for item in batch]

            # 배치 내 작업은 동시에 실행
            batch_results = await self.gather_with_concurrency(batch_tasks)
            all_results.extend(batch_results)

            # 다음 배치 전 지연
            if i + batch_size < len(items) and batch_delay > 0:
                await asyncio.sleep(batch_delay)

        return all_results


def async_timed():
    """비동기 함수 실행 시간 측정 데코레이터"""

    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                end = time.time()
                print(f"⏱️ {func.__name__} 실행 시간: {end - start:.2f}초")

        return wrapped

    return wrapper


async def retry_async(
    coro, max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0
):
    """
    비동기 작업 재시도 유틸리티

    Args:
        coro: 재시도할 코루틴
        max_retries: 최대 재시도 횟수
        delay: 초기 지연 시간 (초)
        backoff_factor: 지연 시간 증가 계수

    Returns:
        코루틴 실행 결과
    """
    retries = 0
    last_exception = None

    while retries < max_retries:
        try:
            return await coro
        except Exception as e:
            last_exception = e
            retries += 1

            if retries >= max_retries:
                break

            wait_time = delay * (backoff_factor ** (retries - 1))
            print(f"재시도 {retries}/{max_retries}: {e} (대기: {wait_time:.1f}초)")
            await asyncio.sleep(wait_time)

    raise last_exception

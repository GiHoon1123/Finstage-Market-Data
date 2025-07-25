"""
비동기 API 클라이언트

FastAPI의 비동기 기능을 활용한 API 클라이언트로,
I/O 바운드 작업을 효율적으로 처리합니다.
"""

import asyncio
import aiohttp
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from app.common.utils.async_executor import async_timed, retry_async, AsyncExecutor


class AsyncApiClient:
    """비동기 API 클라이언트"""

    def __init__(self, base_url: str = "", timeout: int = 30):
        """
        Args:
            base_url: API 기본 URL
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
        self._last_request_time = 0
        self.rate_limit_delay = 0.5  # 기본 요청 간격 (초)

    async def _ensure_session(self):
        """세션이 없으면 생성"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)

    async def _wait_for_rate_limit(self):
        """속도 제한 준수를 위한 대기"""
        now = time.time()
        elapsed = now - self._last_request_time

        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)

        self._last_request_time = time.time()

    async def get(self, url: str, params: Dict = None) -> Any:
        """
        비동기 GET 요청

        Args:
            url: 요청 URL (base_url이 설정된 경우 상대 경로)
            params: URL 쿼리 파라미터

        Returns:
            응답 데이터 (JSON)
        """
        await self._ensure_session()
        await self._wait_for_rate_limit()

        full_url = f"{self.base_url}{url}" if self.base_url else url

        async with self.session.get(full_url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def post(self, url: str, data: Dict = None, json: Dict = None) -> Any:
        """
        비동기 POST 요청

        Args:
            url: 요청 URL (base_url이 설정된 경우 상대 경로)
            data: 폼 데이터
            json: JSON 데이터

        Returns:
            응답 데이터 (JSON)
        """
        await self._ensure_session()
        await self._wait_for_rate_limit()

        full_url = f"{self.base_url}{url}" if self.base_url else url

        async with self.session.post(full_url, data=data, json=json) as response:
            response.raise_for_status()
            return await response.json()

    async def get_with_retry(
        self, url: str, params: Dict = None, max_retries: int = 3
    ) -> Any:
        """재시도 로직이 포함된 GET 요청"""
        return await retry_async(self.get(url, params), max_retries=max_retries)

    async def fetch_multiple(
        self,
        urls: List[str],
        params: Dict = None,
        concurrency: int = 5,
        delay: float = 0.5,
    ) -> List[Any]:
        """
        여러 URL을 병렬로 요청

        Args:
            urls: 요청할 URL 목록
            params: 모든 요청에 적용할 공통 파라미터
            concurrency: 최대 동시 요청 수
            delay: 요청 간 지연 시간 (초)

        Returns:
            각 URL의 응답 데이터 리스트
        """

        await self._ensure_session()

        # 세마포어로 동시성 제한
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_with_semaphore(url):
            """세마포어로 제한된 요청"""
            async with semaphore:
                await self._wait_for_rate_limit()
                full_url = f"{self.base_url}{url}" if self.base_url else url

                try:
                    async with self.session.get(full_url, params=params) as response:
                        response.raise_for_status()
                        return await response.json()
                except Exception as e:
                    print(f"URL {url} 요청 실패: {e}")
                    return None

        # 모든 요청 실행
        tasks = []
        for url in urls:
            # 요청 간 약간의 지연
            if tasks:
                await asyncio.sleep(delay)
            tasks.append(fetch_with_semaphore(url))

        # 모든 요청 완료 대기
        return await asyncio.gather(*tasks)

    async def close(self):
        """세션 종료"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        await self.close()

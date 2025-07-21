"""
API 호출 최적화 유틸리티
"""

import time
import random
import requests
from functools import wraps
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta


class RateLimiter:
    """API 호출 속도 제한 관리"""

    def __init__(self, calls_per_second: float = 2.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0

    def wait_if_needed(self):
        """필요한 경우 대기"""
        current_time = time.time()
        elapsed = current_time - self.last_call_time

        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            time.sleep(wait_time)

        self.last_call_time = time.time()


class ApiCache:
    """API 응답 캐싱"""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 가져오기"""
        if key not in self.cache:
            return None

        entry = self.cache[key]
        if datetime.now() > entry["expires"]:
            # 만료된 항목 삭제
            del self.cache[key]
            return None

        return entry["data"]

    def set(self, key: str, data: Any, ttl: Optional[int] = None) -> None:
        """캐시에 값 저장"""
        # 캐시 크기 제한 확인
        if len(self.cache) >= self.max_size:
            # 가장 오래된 항목 삭제
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["expires"])
            del self.cache[oldest_key]

        # 만료 시간 설정
        ttl = ttl or self.ttl_seconds
        expires = datetime.now() + timedelta(seconds=ttl)

        # 캐시에 저장
        self.cache[key] = {"data": data, "expires": expires}


class OptimizedApiClient:
    """최적화된 API 클라이언트"""

    def __init__(self, base_url: str = "", rate_limit: float = 2.0):
        self.base_url = base_url
        self.rate_limiter = RateLimiter(rate_limit)
        self.cache = ApiCache()
        self.session = requests.Session()

    def get(
        self,
        url: str,
        params: Dict = None,
        use_cache: bool = True,
        cache_ttl: int = 3600,
    ) -> Any:
        """GET 요청 수행"""
        full_url = f"{self.base_url}{url}" if self.base_url else url
        cache_key = f"{full_url}?{str(params)}" if params else full_url

        # 캐시 확인
        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                return cached_data

        # 속도 제한 적용
        self.rate_limiter.wait_if_needed()

        # 요청 수행
        response = self.session.get(full_url, params=params)
        response.raise_for_status()
        data = response.json()

        # 캐시에 저장
        if use_cache:
            self.cache.set(cache_key, data, cache_ttl)

        return data

    def post(self, url: str, data: Dict = None, json: Dict = None) -> Any:
        """POST 요청 수행"""
        full_url = f"{self.base_url}{url}" if self.base_url else url

        # 속도 제한 적용
        self.rate_limiter.wait_if_needed()

        # 요청 수행
        response = self.session.post(full_url, data=data, json=json)
        response.raise_for_status()
        return response.json()

    def close(self):
        """세션 종료"""
        self.session.close()


def adaptive_retry(
    max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0
):
    """적응형 재시도 데코레이터"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (requests.RequestException, ConnectionError) as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e

                    # 지수 백오프 + 약간의 무작위성
                    delay = min(
                        base_delay * (2 ** (retries - 1)) + random.uniform(0, 1),
                        max_delay,
                    )
                    print(
                        f"API 호출 실패, {retries}/{max_retries} 재시도 ({delay:.2f}초 후): {e}"
                    )
                    time.sleep(delay)

            return None  # 여기까지 오면 안 됨

        return wrapper

    return decorator
